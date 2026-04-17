from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: Literal["slice.requested", "slice.completed", "slice.failed"]
    created_at: datetime
    source: str
    spec_version: str


class SliceRequestedMinioPaths(BaseModel):
    """Пути объектов в MinIO (docs/asyncapi.yml SliceRequestedPayload.minio_paths)."""

    model_config = ConfigDict(extra="forbid")

    stl_file: str
    printer_profile: str
    process_profile: str
    filament_profile: str


class SliceRequestedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: UUID
    customer_id: UUID
    priority: Literal["low", "normal", "high"] = "normal"
    minio_paths: SliceRequestedMinioPaths


class SliceRequestedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: Literal["slice.requested"]
    created_at: datetime
    source: str
    spec_version: str
    payload: SliceRequestedPayload


class SliceCompletedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: UUID
    status: Literal["completed"] = "completed"
    gcode_object_key: str
    print_time_sec: int = Field(ge=1)
    filament_weight_g: float = Field(ge=0.001)
    filament_length_m: Optional[float] = None
    slicer_version: Optional[str] = None


class SliceCompletedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: Literal["slice.completed"]
    created_at: datetime
    source: str
    spec_version: str
    payload: SliceCompletedPayload


class SliceFailedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: UUID
    error_code: str
    error_message: str
    retryable: bool


class SliceFailedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: Literal["slice.failed"]
    created_at: datetime
    source: str
    spec_version: str
    payload: SliceFailedPayload
