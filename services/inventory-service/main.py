from fastapi import FastAPI, APIRouter

app = FastAPI(
    title="Inventory Service",
    docs_url="/api/inventory/docs",
    openapi_url="/api/inventory/openapi.json",
)

router = APIRouter(prefix="/api/inventory")


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "inventory-service", "ready": True}


@router.get("")
async def root():
    return {"message": "Welcome to Inventory Service"}


app.include_router(router)
