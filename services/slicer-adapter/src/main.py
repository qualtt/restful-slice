import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.clients.rabbit_client import start_consuming
from src.core.processor import process_slicing_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

worker_thread: threading.Thread | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global worker_thread
    worker_thread = threading.Thread(
        target=start_consuming,
        args=("slicing.jobs", process_slicing_task),
        daemon=True,
        name="rabbit-slicing-worker",
    )
    worker_thread.start()
    logger.info("Background worker thread started.")
    yield


app = FastAPI(title="Slicer Adapter", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
