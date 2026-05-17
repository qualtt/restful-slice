from fastapi import FastAPI, APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, UUID4
from typing import Optional

from core.stock import InventoryStock, InsufficientStockError
from core.calculator import Calculator

app = FastAPI(
    title="Inventory Service",
    docs_url="/api/inventory/docs",
    openapi_url="/api/inventory/openapi.json",
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


router = APIRouter(tags=["Inventory"])
internal_router = APIRouter(prefix="/api/internal/inventory", tags=["Internal"])
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
    orderId: UUID4
    profileId: int
    weightGrams: float


class StatusUpdateRequest(BaseModel):
    status: str


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


@router.get("/api/inventory/profiles")
async def list_profiles(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    materialType: Optional[str] = None,
    isEnabled: bool = True,
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


@router.get("/api/inventory/profiles/{profileId}")
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


@router.get("/api/inventory/materials")
async def list_materials(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    isActive: bool = True,
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


@router.get("/api/inventory/materials/{materialId}")
async def get_material(materialId: int):
    for m in MATERIALS_DB:
        if m["materialId"] == materialId:
            m_copy = m.copy()
            m_copy["remainingGrams"] = stock_db.get_available(materialId)
            return m_copy
    return JSONResponse(
        status_code=404, content={"code": "NOT_FOUND", "message": "Resource not found"}
    )


@internal_router.post("/reserve")
async def reserve_material(payload: ReserveRequest):
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
