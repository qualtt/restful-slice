import json
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, UUID4
from typing import Dict, Any, Optional, List

from core.order_manager import OrderManager, OrderStatus
from core.config import get_settings
from core.minio_client import OrderMinioClient
from core.rabbit_client import publish_slice_requested, start_results_consumer

logger = logging.getLogger(__name__)


def fail_order(order_id: str, error_message: str) -> None:
    try:
        order_db.update_status(
            order_id,
            OrderStatus.FAILED.value,
            error_message=error_message,
        )
    except Exception:
        logger.exception("Failed to update order %s to FAILED", order_id)


def handle_slicing_result(event_json: str) -> None:
    data = json.loads(event_json)
    event_type = data.get("event_type")
    payload = data.get("payload", {})
    order_id = payload.get("order_id")
    if not order_id:
        return

    if event_type == "slice.completed":
        weight = payload.get("filament_weight_g", 0.001)
        print_time = payload.get("print_time_sec", 1)

        settings = get_settings()
        profile_id = None
        try:
            order = order_db.get_order(order_id)
            profile_id = order.get("profileId")
        except KeyError:
            logger.error("Order %s not found when processing slice.completed", order_id)
            return

        price = {"amount": "0.00", "currency": "RUB"}
        if profile_id is not None:
            try:
                resp = httpx.post(
                    f"{settings.inventory_url}/api/internal/inventory/reserve",
                    json={
                        "orderId": order_id,
                        "profileId": profile_id,
                        "weightGrams": weight,
                    },
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    price = resp.json().get("price", price)
                else:
                    error_message = (
                        f"Inventory reserve failed with {resp.status_code}: {resp.text}"
                    )
                    logger.warning(error_message)
                    fail_order(order_id, error_message)
                    return
            except Exception as exc:
                logger.exception(
                    "Failed to call inventory reserve for order %s", order_id
                )
                fail_order(order_id, f"Inventory reserve failed: {exc}")
                return

        order_db.update_status(
            order_id,
            OrderStatus.PRICED.value,
            slicing_result={
                "weightGrams": weight,
                "printTimeSeconds": print_time,
                "price": price,
            },
        )

    elif event_type == "slice.failed":
        error_msg = payload.get("error_message", "Slicing failed")
        fail_order(order_id, error_msg)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # На случай любого преждевременного импортного вызова get_settings() без полного окружения.
    get_settings.cache_clear()
    start_results_consumer(handle_slicing_result)
    yield


app = FastAPI(
    title="Order Service",
    docs_url="/api/orders/docs",
    openapi_url="/api/orders/openapi.json",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": "INTERNAL_ERROR"
                if exc.status_code >= 500
                else str(exc.detail).upper(),
                "message": str(exc.detail),
            },
        )
    logger.exception("%s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )


router = APIRouter(prefix="/api/orders", tags=["Orders"])
telemetry_router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])
order_db = OrderManager()


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class PaginationMeta(BaseModel):
    total: int
    page: int
    pageSize: int


class Money(BaseModel):
    amount: str
    currency: str


class UploadedFileResponse(BaseModel):
    fileId: UUID4
    filename: str
    sizeBytes: int
    uploadedAt: str


class CreateOrderRequest(BaseModel):
    fileId: UUID4
    profileId: int


class SlicingResult(BaseModel):
    weightGrams: float
    printTimeSeconds: int
    price: Money


class OrderResponse(BaseModel):
    orderId: UUID4
    status: OrderStatus
    fileId: UUID4
    profileId: int
    slicingResult: Optional[SlicingResult] = None
    errorMessage: Optional[str] = None
    createdAt: str
    updatedAt: str


class OrderListResponse(BaseModel):
    data: List[OrderResponse]
    meta: PaginationMeta


class TelemetryEvent(BaseModel):
    id: str
    name: str
    ts: str
    sessionId: str
    route: str
    consentVersion: str
    context: Dict[str, Any]
    data: Dict[str, Any]


class TelemetryBatchRequest(BaseModel):
    source: str
    events: List[TelemetryEvent]


@router.post("/files", response_model=UploadedFileResponse, status_code=201)
async def upload_stl_file(file: UploadFile = File(...)):
    name_lower = (file.filename or "").lower()
    allowed_exts = (".stl", ".3mf", ".step", ".stp")
    allowed_mimes = {
        "model/stl",
        "model/3mf",
        "model/step",
        "application/step",
        "application/octet-stream",
    }
    if not name_lower.endswith(allowed_exts) and file.content_type not in allowed_mimes:
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_FILE_TYPE",
                "message": "Only STL, 3MF, or STEP files are accepted",
            },
        )

    data = await file.read()
    size = len(data)
    if size > 100 * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={
                "code": "FILE_TOO_LARGE",
                "message": "File size exceeds 100 MB limit",
            },
        )

    file_record = order_db.save_file(file.filename, size)

    try:
        settings = get_settings()
        minio = OrderMinioClient(settings)
        object_key = minio.upload_stl(file_record["fileId"], file.filename, data)
        order_db.save_file_object_key(file_record["fileId"], object_key)
    except Exception:
        logger.exception("MinIO upload failed for file %s", file_record["fileId"])

    return file_record


@router.post("", response_model=OrderResponse, status_code=202)
async def create_order(payload: CreateOrderRequest):
    try:
        order = order_db.create_order(str(payload.fileId), payload.profileId)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content={
                "code": "FILE_NOT_FOUND",
                "message": "STL file with given fileId does not exist",
            },
        )

    try:
        file_record = order_db.get_file(str(payload.fileId))
        object_key = file_record.get(
            "objectKey"
        ) or f"stl/orders/{payload.fileId}/{file_record.get('filename', 'model.stl')}"
        order_db.update_status(order["orderId"], OrderStatus.SLICING.value)
        publish_slice_requested(order["orderId"], object_key, payload.profileId)
    except Exception:
        logger.exception(
            "Failed to publish slice.requested for order %s", order["orderId"]
        )

    return order_db.get_order(order["orderId"])


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
):
    orders = order_db.list_orders()
    if status is not None:
        orders = [o for o in orders if o["status"] == status.value]

    total = len(orders)
    start = (page - 1) * pageSize
    end = start + pageSize

    return {
        "data": orders[start:end],
        "meta": {"total": total, "page": page, "pageSize": pageSize},
    }


@router.get("/{orderId}", response_model=OrderResponse)
async def get_order(orderId: UUID4):
    try:
        return order_db.get_order(str(orderId))
    except KeyError:
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": "Resource not found"},
        )


@router.delete("/{orderId}", response_model=OrderResponse)
async def cancel_order(orderId: UUID4):
    try:
        order = order_db.get_order(str(orderId))
        if order["status"] not in [
            OrderStatus.PENDING.value,
            OrderStatus.SLICING.value,
            OrderStatus.PRICED.value,
        ]:
            return JSONResponse(
                status_code=409,
                content={
                    "code": "ORDER_NOT_CANCELLABLE",
                    "message": f"Order in status '{order['status']}' cannot be cancelled",
                },
            )
        return order_db.update_status(str(orderId), OrderStatus.CANCELLED.value)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": "Resource not found"},
        )


@telemetry_router.post("/events", status_code=202)
async def receive_telemetry_events(payload: TelemetryBatchRequest):
    from core.database import db_stub

    for event in payload.events:
        try:
            db_stub.insert(
                table="telemetry_events",
                record_id=event.id,
                data={
                    "session_id": event.sessionId,
                    "event_name": event.name,
                    "route": event.route,
                    "consent_version": event.consentVersion,
                    "context": event.context,
                    "data": event.data,
                    "client_ts": event.ts,
                },
            )
        except Exception:
            logger.exception("Failed to insert telemetry event %s", event.id)

    return {"status": "accepted", "processed": len(payload.events)}


app.include_router(router)
app.include_router(telemetry_router)
