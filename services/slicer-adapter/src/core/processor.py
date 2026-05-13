import logging
import shutil
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from src.clients.minio_client import MinioClient
from src.clients.orca_client import OrcaSlicerClient
from src.clients.rabbit_client import RequeueMessageError, publish_event_with_retries
from src.core.config import get_settings
from src.schemas.events import (
    SliceCompletedEvent,
    SliceCompletedPayload,
    SliceFailedEvent,
    SliceFailedPayload,
    SliceRequestedEvent,
)
from src.schemas.orca import OrcaSliceMetadata

logger = logging.getLogger(__name__)

RESULTS_QUEUE = "slicing.results"


def _minio_download_keys(payload: SliceRequestedEvent) -> list[str]:
    mp = payload.payload.minio_paths
    return [
        mp.stl_file,
        mp.printer_profile,
        mp.process_profile,
        mp.filament_profile,
    ]


def _orca_profile_paths(
    payload: SliceRequestedEvent,
    local_map: dict[str, str],
) -> dict[str, str]:
    mp = payload.payload.minio_paths
    return {
        "printerProfile": local_map[mp.printer_profile],
        "presetProfile": local_map[mp.process_profile],
        "filamentProfile": local_map[mp.filament_profile],
    }


def process_slicing_task(event_json: str) -> None:
    settings = get_settings()
    minio_client = MinioClient(settings)
    orca_client = OrcaSlicerClient(settings)

    try:
        job = SliceRequestedEvent.model_validate_json(event_json)
    except ValidationError:
        logger.exception("Invalid slice.requested payload")
        raise

    tmp = f"/temp/{uuid4()}"
    try:
        keys = _minio_download_keys(job)
        local_map = minio_client.download_files(keys, tmp)
        stl_local = local_map[job.payload.minio_paths.stl_file]
        profile_paths = _orca_profile_paths(job, local_map)

        gcode_path, raw_meta = orca_client.slice_model(stl_local, profile_paths)
        meta = OrcaSliceMetadata.model_validate(raw_meta)

        gcode_key = f"gcode/orders/{job.payload.order_id}/result.gcode"
        minio_client.upload_file(gcode_path, gcode_key)

        print_time = meta.print_time_sec or 1
        if print_time < 1:
            print_time = 1
        weight = meta.filament_weight_g or 0.001
        if weight < 0.001:
            weight = 0.001
        filament_length_m = (
            (meta.filament_length_mm / 1000.0)
            if meta.filament_length_mm is not None
            else None
        )

        completed = SliceCompletedEvent(
            event_id=uuid4(),
            event_type="slice.completed",
            created_at=datetime.now(timezone.utc),
            source=settings.service_name,
            spec_version=settings.event_spec_version,
            payload=SliceCompletedPayload(
                order_id=job.payload.order_id,
                status="completed",
                gcode_object_key=gcode_key,
                print_time_sec=print_time,
                filament_weight_g=weight,
                filament_length_m=filament_length_m,
                slicer_version=meta.slicer_version,
            ),
        )
        publish_event_with_retries(RESULTS_QUEUE, completed)
    except RequeueMessageError:
        raise
    except Exception as exc:
        logger.exception("Slicing failed for order_id=%s", job.payload.order_id)
        failed = SliceFailedEvent(
            event_id=uuid4(),
            event_type="slice.failed",
            created_at=datetime.now(timezone.utc),
            source=settings.service_name,
            spec_version=settings.event_spec_version,
            payload=SliceFailedPayload(
                order_id=job.payload.order_id,
                error_code=type(exc).__name__.upper().replace("EXCEPTION", "")[:32]
                or "SLICE_ERROR",
                error_message=str(exc)[:4000],
                retryable=False,
            ),
        )
        publish_event_with_retries(RESULTS_QUEUE, failed)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
