from typing import Optional

from pydantic import BaseModel, ConfigDict


class OrcaSliceMetadata(BaseModel):
    """Метаданные успешного ответа синхронного POST /slice (swagger: заголовки ответа 200)."""

    model_config = ConfigDict(extra="ignore")

    print_time_sec: Optional[int] = None
    filament_weight_g: Optional[float] = None
    filament_length_mm: Optional[float] = None
    slicer_version: Optional[str] = None
