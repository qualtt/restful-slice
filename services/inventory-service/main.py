from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI, APIRouter, HTTPException, Query, Request, Security
from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional

from core.stock import InventoryStock, InsufficientStockError
from core.calculator import Calculator

_API_KEY_TO_USER_ID = {
    "demo-api-key": "user-0001",
    "sample-api-key": "user-0002",
}
SWAGGER_UI_DEFAULT_API_KEY = "demo-api-key"
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


@lru_cache
def resolve_user_id_from_api_key(api_key: str) -> str:
    return _API_KEY_TO_USER_ID.get(api_key, "anonymous")


def get_request_user_id(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if not api_key:
        return "anonymous"
    return resolve_user_id_from_api_key(api_key)


app = FastAPI(
    title="Inventory Service",
    docs_url=None,
    openapi_url="/api/inventory/openapi.json",
)
app.mount(
    "/api/inventory/docs-assets",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="inventory-docs-assets",
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
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )


router = APIRouter(tags=["Inventory"], dependencies=[Security(api_key_scheme)])
internal_router = APIRouter(
    prefix="/api/internal/inventory",
    tags=["Internal"],
    dependencies=[Security(api_key_scheme)],
)
health_router = APIRouter(tags=["Health"])

stock_db = InventoryStock()
if not stock_db.db.select("inventory", "1"):
    stock_db.db.insert("inventory", "1", {"material_id": 1, "total_grams": 2500.0})
if not stock_db.db.select("inventory", "2"):
    stock_db.db.insert("inventory", "2", {"material_id": 2, "total_grams": 1500.0})


class PaginationMeta(BaseModel):
    total: int
    page: int
    pageSize: int


class Money(BaseModel):
    amount: str
    currency: str


class Material(BaseModel):
    materialId: int
    label: str
    materialType: str
    remainingGrams: float
    costPerGram: Money
    isActive: bool
    description: Optional[str] = None


class PrinterPreset(BaseModel):
    printerId: int
    modelName: str
    orcaPrinterId: str


class ProcessPreset(BaseModel):
    processId: int
    name: str
    orcaProcessId: str


class PrintProfile(BaseModel):
    profileId: int
    displayName: str
    printer: PrinterPreset
    material: Material
    process: ProcessPreset
    markupPercent: float
    isEnabled: bool
    description: Optional[str] = None


class ReserveRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "orderId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "profileId": 3,
                "weightGrams": 47.3,
            }
        }
    )

    orderId: UUID4 = Field(..., examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])
    profileId: int = Field(..., examples=[3])
    weightGrams: float = Field(..., examples=[47.3])


class StatusUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"status": "consumed"}}
    )

    status: str = Field(..., examples=["consumed"])


class ProfileListResponse(BaseModel):
    data: list[PrintProfile]
    meta: PaginationMeta


class MaterialListResponse(BaseModel):
    data: list[Material]
    meta: PaginationMeta


class ReserveResponse(BaseModel):
    reservationId: UUID4
    reservedWeightGrams: float
    price: Money


def _swagger_oauth2_redirect_path(request: Request) -> str:
    if app.swagger_ui_oauth2_redirect_url:
        return app.swagger_ui_oauth2_redirect_url
    base_path = request.scope.get("root_path", "").rstrip("/")
    return f"{base_path}/docs/oauth2-redirect"


def _swagger_openapi_url(request: Request) -> str:
    openapi_url = app.openapi_url or "/openapi.json"
    root_path = request.scope.get("root_path", "").rstrip("/")
    if openapi_url.startswith(("http://", "https://")):
        return openapi_url
    return f"{root_path}{openapi_url}"


def _render_swagger_html(title: str, openapi_url: str, oauth2_redirect_url: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="/api/inventory/docs-assets/swagger-ui/swagger-ui.css">
</head>
<body>
  <div
    id="swagger-ui"
    data-openapi-url="{openapi_url}"
    data-oauth2-redirect-url="{oauth2_redirect_url}"
    data-default-api-key="{SWAGGER_UI_DEFAULT_API_KEY}"
    data-title="{title}"
  ></div>
  <script src="/api/inventory/docs-assets/swagger-ui/swagger-ui-bundle.js"></script>
  <script src="/api/inventory/docs-assets/swagger-ui/docs-bootstrap.js"></script>
</body>
</html>"""


@app.get("/api/inventory/docs", include_in_schema=False)
async def custom_inventory_docs(request: Request) -> HTMLResponse:
    html = _render_swagger_html(
        title=f"{app.title} - Swagger UI",
        openapi_url=_swagger_openapi_url(request),
        oauth2_redirect_url=_swagger_oauth2_redirect_path(request),
    )
    return HTMLResponse(html)


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect() -> HTMLResponse:
    return get_swagger_ui_oauth2_redirect_html()


def _check_schema_and_round_trip() -> dict[str, object]:
    db = stock_db.db
    if not hasattr(db, "_connect") or not hasattr(db, "_core_tables_exist"):
        stock_db.get_stock(1)
        stock_db.get_available(1)
        return {"postgres": "ok", "schema": "ok"}

    conn = db._connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            if not db._core_tables_exist(cur):
                raise RuntimeError("core tables are missing")
            cur.execute("SELECT material_id, total_grams FROM inventory LIMIT 1")
            cur.fetchone()
        return {"postgres": "ok", "schema": "ok"}
    finally:
        conn.close()


@health_router.get("/health/live")
async def health_live():
    return {"status": "healthy"}


@health_router.get("/health/ready")
async def health_ready():
    try:
        return {"status": "healthy", **_check_schema_and_round_trip()}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(exc)[:500]},
        )


@health_router.get("/health")
async def health():
    return await health_ready()


MATERIALS_DB = [
    {
        "materialId": 1,
        "label": "Esun PLA White 1kg",
        "materialType": "PLA",
        "remainingGrams": 2500.0,
        "costPerGram": {"amount": "0.15", "currency": "RUB"},
        "isActive": True,
        "description": "Standard PLA, white",
    },
    {
        "materialId": 2,
        "label": "Creality Generic PETG Black 1kg",
        "materialType": "PETG",
        "remainingGrams": 1500.0,
        "costPerGram": {"amount": "0.18", "currency": "RUB"},
        "isActive": True,
        "description": "Creality Generic PETG, black",
    },
]

PRINTERS_DB = {
    1: {
        "printerId": 1,
        "modelName": "Creality K1C",
        "orcaPrinterId": "creality_k1c_0.4_nozzle",
    }
}

PROCESS_DB = {
    1: {
        "processId": 1,
        "name": "0.20mm Standard",
        "orcaProcessId": "0.20mm_standard_creality_k1c_0.4_nozzle",
    },
    2: {
        "processId": 2,
        "name": "0.24mm Draft",
        "orcaProcessId": "0.24mm_draft_creality_k1c_0.4_nozzle",
    },
    3: {
        "processId": 3,
        "name": "0.12mm Fine",
        "orcaProcessId": "0.12mm_fine_creality_k1c_0.4_nozzle",
    },
}

PROFILES_DB = [
    {
        "profileId": 3,
        "displayName": "PETG Стандарт (K1C)",
        "printer": PRINTERS_DB[1],
        "material": MATERIALS_DB[1],
        "process": PROCESS_DB[1],
        "markupPercent": 1.2,
        "isEnabled": True,
        "description": "Стандартный профиль для прототипов на Creality K1C",
    },
    {
        "profileId": 4,
        "displayName": "PETG Черновой (K1C)",
        "printer": PRINTERS_DB[1],
        "material": MATERIALS_DB[1],
        "process": PROCESS_DB[2],
        "markupPercent": 1.0,
        "isEnabled": True,
        "description": "Быстрый draft-профиль с высотой слоя 0.24 мм для черновых прогонов",
    },
    {
        "profileId": 5,
        "displayName": "PETG Высокое качество (K1C)",
        "printer": PRINTERS_DB[1],
        "material": MATERIALS_DB[1],
        "process": PROCESS_DB[3],
        "markupPercent": 1.35,
        "isEnabled": True,
        "description": "Точный профиль с высотой слоя 0.12 мм для финальных деталей и витринных моделей",
    }
]


@router.get("/api/inventory/profiles", response_model=ProfileListResponse)
async def list_profiles(
    page: int = Query(1, ge=1, examples=[1]),
    pageSize: int = Query(20, ge=1, le=100, examples=[20]),
    materialType: Optional[str] = Query(None, examples=["PETG"]),
    isEnabled: bool = Query(True, examples=[True]),
):
    profiles = [p for p in PROFILES_DB if p["isEnabled"] == isEnabled]
    if materialType:
        profiles = [
            p for p in profiles if p["material"]["materialType"] == materialType
        ]

    for p in profiles:
        p["material"]["remainingGrams"] = stock_db.get_available(
            p["material"]["materialId"]
        )

    start = (page - 1) * pageSize
    end = start + pageSize

    return {
        "data": profiles[start:end],
        "meta": {"total": len(profiles), "page": page, "pageSize": pageSize},
    }


@router.get("/api/inventory/profiles/{profileId}", response_model=PrintProfile)
async def get_profile(profileId: int):
    for p in PROFILES_DB:
        if p["profileId"] == profileId:
            p_copy = p.copy()
            p_copy["material"]["remainingGrams"] = stock_db.get_available(
                p_copy["material"]["materialId"]
            )
            return p_copy
    return JSONResponse(
        status_code=404, content={"code": "NOT_FOUND", "message": "Resource not found"}
    )


@router.get("/api/inventory/materials", response_model=MaterialListResponse)
async def list_materials(
    page: int = Query(1, ge=1, examples=[1]),
    pageSize: int = Query(20, ge=1, le=100, examples=[20]),
    type: Optional[str] = Query(None, examples=["PETG"]),
    isActive: bool = Query(True, examples=[True]),
):
    materials = [m for m in MATERIALS_DB if m["isActive"] == isActive]
    if type:
        materials = [m for m in materials if m["materialType"] == type]

    start = (page - 1) * pageSize
    end = start + pageSize

    mats = materials.copy()[start:end]
    for m in mats:
        m["remainingGrams"] = stock_db.get_available(m["materialId"])

    return {
        "data": mats,
        "meta": {"total": len(materials), "page": page, "pageSize": pageSize},
    }


@router.get("/api/inventory/materials/{materialId}", response_model=Material)
async def get_material(materialId: int):
    for m in MATERIALS_DB:
        if m["materialId"] == materialId:
            m_copy = m.copy()
            m_copy["remainingGrams"] = stock_db.get_available(materialId)
            return m_copy
    return JSONResponse(
        status_code=404, content={"code": "NOT_FOUND", "message": "Resource not found"}
    )


@internal_router.post("/reserve", response_model=ReserveResponse)
async def reserve_material(payload: ReserveRequest, request: Request):
    request.state.user_id = get_request_user_id(request)
    profile = next(
        (
            p
            for p in PROFILES_DB
            if p["profileId"] == payload.profileId and p["isEnabled"]
        ),
        None,
    )
    if not profile:
        return JSONResponse(
            status_code=404,
            content={
                "code": "PROFILE_NOT_FOUND",
                "message": f"Print profile {payload.profileId} does not exist or is disabled",
            },
        )

    mat_id = profile["material"]["materialId"]
    cost_per_gram = float(profile["material"]["costPerGram"]["amount"])
    currency = profile["material"]["costPerGram"]["currency"]

    try:
        reserved_weight = stock_db.normalize_reservation_amount(payload.weightGrams)
        res_id = stock_db.reserve_material(
            str(payload.orderId), mat_id, reserved_weight
        )
        cost = Calculator.calculate_cost(
            reserved_weight, cost_per_gram, profile["markupPercent"]
        )
        return {
            "reservationId": res_id,
            "reservedWeightGrams": reserved_weight,
            "price": {"amount": f"{cost:.2f}", "currency": currency},
        }
    except InsufficientStockError as e:
        return JSONResponse(
            status_code=409,
            content={"code": "INSUFFICIENT_MATERIAL", "message": str(e)},
        )


@internal_router.patch("/reservations/{orderId}/status")
async def update_reservation_status(orderId: UUID4, payload: StatusUpdateRequest):
    if payload.status not in ["consumed", "cancelled"]:
        return JSONResponse(
            status_code=400,
            content={
                "code": "INVALID_STATUS",
                "message": "Status must be 'consumed' or 'cancelled'",
            },
        )

    try:
        if payload.status == "consumed":
            stock_db.confirm_reservation(str(orderId))
        else:
            stock_db.cancel_reservation(str(orderId))
        return {}
    except KeyError:
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": "Reservation not found"},
        )


app.include_router(router)
app.include_router(internal_router)
app.include_router(health_router)
