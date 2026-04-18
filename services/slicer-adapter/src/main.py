import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.clients.rabbit_client import JOBS_QUEUE, check_broker_reachable, start_consuming
from src.core.processor import process_slicing_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

worker_thread: threading.Thread | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global worker_thread
    worker_thread = threading.Thread(
        target=start_consuming,
        args=(JOBS_QUEUE, process_slicing_task),
        daemon=True,
        name="rabbit-slicing-worker",
    )
    worker_thread.start()
    logger.info("Background worker thread started.")
    yield


app = FastAPI(title="Slicer Adapter", lifespan=lifespan)


@app.get("/health")
def health_check():
    try:
        check_broker_reachable()
    except Exception as exc:
        logger.warning("Health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "rabbitmq": str(exc)[:500]},
        )
    return {"status": "healthy", "rabbitmq": "ok"}
