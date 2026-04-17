from fastapi import FastAPI, APIRouter

app = FastAPI(
    title="Order Service",
    docs_url="/api/orders/docs",
    openapi_url="/api/orders/openapi.json",
)

router = APIRouter(prefix="/api/orders")


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "order-service", "ready": True}


@router.get("")
async def root():
    return {"message": "Welcome to Order Service"}


app.include_router(router)
