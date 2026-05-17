import logging
import threading
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.clients.rabbit_client import (
    JOBS_QUEUE,
    check_broker_reachable,
    get_consumer_state,
    start_consuming,
)
from src.clients.minio_client import MinioClient
from src.core.config import get_settings
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


def _check_minio() -> str:
    settings = get_settings()
    client = MinioClient(settings)
    client.check_bucket_access()
    return "ok"


def _check_orca() -> str:
    settings = get_settings()
    resp = requests.get(f"{settings.orca_api_url.rstrip('/')}/health", timeout=3.0)
    resp.raise_for_status()
    return "ok"


@app.get("/health/live")
def health_live():
    state = get_consumer_state()
    return {
        "status": "healthy",
        "worker_thread_alive": bool(worker_thread and worker_thread.is_alive()),
        "last_success": state["last_success"],
        "last_error": state["last_error"],
    }


def _health_ready_payload() -> dict[str, object]:
    payload = {
        "status": "healthy",
        "rabbitmq": "ok",
        "minio": "ok",
        "orca": "ok",
    }
    try:
        check_broker_reachable()
        payload["minio"] = _check_minio()
        payload["orca"] = _check_orca()
    except Exception as exc:
        logger.warning("Health check failed: %s", exc)
        raise RuntimeError(str(exc)) from exc
    state = get_consumer_state()
    payload["worker_thread_alive"] = bool(worker_thread and worker_thread.is_alive())
    payload["last_success"] = state["last_success"]
    payload["last_error"] = state["last_error"]
    if not payload["worker_thread_alive"]:
        raise RuntimeError("worker thread not running")
    return payload


@app.get("/health/ready")
def health_check():
    try:
        return _health_ready_payload()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(exc)[:500]},
        )


@app.get("/health")
def health():
    return health_check()


@app.get("/health/live")
def health_live():
    return {
        "status": "healthy",
        "worker_thread_alive": bool(worker_thread and worker_thread.is_alive()),
        "last_success": get_consumer_state()["last_success"],
        "last_error": get_consumer_state()["last_error"],
    }


@app.get("/health/ready")
def health_ready():
    return health_check()
