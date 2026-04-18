from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, UUID4, Field
from typing import Dict, Any, Optional, List
from math import ceil
from core.order_manager import OrderManager, InvalidStatusTransitionError, OrderStatus

app = FastAPI(
    title="Order Service",
    docs_url="/api/orders/docs",
    openapi_url="/api/orders/openapi.json",
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": "INTERNAL_ERROR" if exc.status_code >= 500 else str(exc.detail).upper(), "message": str(exc.detail)}
        )
    return JSONResponse(status_code=500, content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"})

router = APIRouter(prefix="/api/orders", tags=["Orders"])
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

@router.post("/files", response_model=UploadedFileResponse, status_code=201)
async def upload_stl_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.stl') and file.content_type not in ['model/stl', 'application/octet-stream']:
        return JSONResponse(status_code=400, content={"code": "INVALID_FILE_TYPE", "message": "Only STL files are accepted"})
    
    file.file.seek(0, 2)
    size = file.file.tell()
    if size > 100 * 1024 * 1024:
        return JSONResponse(status_code=413, content={"code": "FILE_TOO_LARGE", "message": "File size exceeds 100 MB limit"})
        
    return order_db.save_file(file.filename, size)

@router.post("", response_model=OrderResponse, status_code=202)
async def create_order(payload: CreateOrderRequest):
    try:
        return order_db.create_order(str(payload.fileId), payload.profileId)
    except KeyError:
        return JSONResponse(status_code=404, content={"code": "FILE_NOT_FOUND", "message": "STL file with given fileId does not exist"})

@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None
):
    orders = order_db.list_orders()
    if status is not None:
        orders = [o for o in orders if o["status"] == status.value]
    
    total = len(orders)
    start = (page - 1) * pageSize
    end = start + pageSize
    
    return {
        "data": orders[start:end],
        "meta": {"total": total, "page": page, "pageSize": pageSize}
    }

@router.get("/{orderId}", response_model=OrderResponse)
async def get_order(orderId: UUID4):
    try:
        return order_db.get_order(str(orderId))
    except KeyError:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Resource not found"})

@router.delete("/{orderId}", response_model=OrderResponse)
async def cancel_order(orderId: UUID4):
    try:
        order = order_db.get_order(str(orderId))
        if order["status"] not in [OrderStatus.PENDING.value, OrderStatus.SLICING.value, OrderStatus.PRICED.value]:
            return JSONResponse(
                status_code=409, 
                content={"code": "ORDER_NOT_CANCELLABLE", "message": f"Order in status '{order['status']}' cannot be cancelled"}
            )
        return order_db.update_status(str(orderId), OrderStatus.CANCELLED.value)
    except KeyError:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Resource not found"})

app.include_router(router)
