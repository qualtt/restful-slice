
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.core.processor import RESULTS_QUEUE, process_slicing_task
from src.schemas.events import SliceCompletedEvent, SliceFailedEvent


@patch("src.core.processor.shutil.rmtree")
@patch("src.core.processor.publish_event_with_retries")
@patch("src.core.processor.OrcaSlicerClient")
@patch("src.core.processor.MinioClient")
@patch("src.core.processor.get_settings")
def test_process_slicing_task_success_publishes_completed(
    mock_get_settings,
    mock_minio_cls,
    mock_orca_cls,
    mock_publish,
    _mock_rmtree,
    slice_requested_event_json: str,
) -> None:
    settings = MagicMock()
    settings.service_name = "slicer-adapter"
    settings.event_spec_version = "1.0.0"
    mock_get_settings.return_value = settings

    minio = mock_minio_cls.return_value
    stl_key = "stl/orders/22222222/model.stl"
    printer_key = "profiles/printers/prusa_mk3s.json"
    process_key = "profiles/process/0_20mm_quality.json"
    filament_key = "profiles/filaments/generic_pla.json"
    stl_local = "/temp/abc/stl__orders__22222222__model.stl"
    printer_local = "/temp/abc/profiles__printers__prusa_mk3s.json"
    process_local = "/temp/abc/profiles__process__0_20mm_quality.json"
    filament_local = "/temp/abc/profiles__filaments__generic_pla.json"
    minio.download_files.return_value = {
        stl_key: stl_local,
        printer_key: printer_local,
        process_key: process_local,
        filament_key: filament_local,
    }

    orca = mock_orca_cls.return_value
    gcode_local = "/temp/abc/result.gcode"
    orca.slice_model.return_value = (
        gcode_local,
        {
            "print_time_sec": 3600,
            "filament_weight_g": 12.5,
            "filament_length_mm": 4000.0,
            "slicer_version": "OrcaSlicer 2.3.0",
        },
    )

    process_slicing_task(slice_requested_event_json)

    minio.download_files.assert_called_once()
    args, _ = minio.download_files.call_args
    assert args[0] == [stl_key, printer_key, process_key, filament_key]

    expected_profiles = {
        "printerProfile": printer_local,
        "presetProfile": process_local,
        "filamentProfile": filament_local,
    }
    orca.slice_model.assert_called_once_with(stl_local, expected_profiles)

    gcode_key = "gcode/orders/22222222-2222-2222-2222-222222222222/result.gcode"
    minio.upload_file.assert_called_once_with(gcode_local, gcode_key)

    mock_publish.assert_called_once()
    queue, event = mock_publish.call_args[0]
    assert queue == RESULTS_QUEUE
    assert isinstance(event, SliceCompletedEvent)
    assert event.event_type == "slice.completed"
    assert str(event.payload.order_id) == "22222222-2222-2222-2222-222222222222"
    assert event.payload.gcode_object_key == gcode_key
    assert event.payload.print_time_sec == 3600
    assert event.payload.filament_weight_g == 12.5
    assert event.payload.filament_length_m == pytest.approx(4.0)
    assert event.payload.slicer_version == "OrcaSlicer 2.3.0"


@patch("src.core.processor.shutil.rmtree")
@patch("src.core.processor.publish_event_with_retries")
@patch("src.core.processor.OrcaSlicerClient")
@patch("src.core.processor.MinioClient")
@patch("src.core.processor.get_settings")
def test_process_slicing_task_orca_failure_publishes_failed(
    mock_get_settings,
    mock_minio_cls,
    mock_orca_cls,
    mock_publish,
    _mock_rmtree,
    slice_requested_event_json: str,
) -> None:
    mock_get_settings.return_value = MagicMock(
        service_name="slicer-adapter",
        event_spec_version="1.0.0",
    )

    minio = mock_minio_cls.return_value
    minio.download_files.return_value = {
        "stl/orders/22222222/model.stl": "/tmp/x.stl",
        "profiles/printers/prusa_mk3s.json": "/tmp/p.json",
        "profiles/process/0_20mm_quality.json": "/tmp/pr.json",
        "profiles/filaments/generic_pla.json": "/tmp/f.json",
    }

    mock_orca_cls.return_value.slice_model.side_effect = RuntimeError(
        "Orca slice failed (500)"
    )

    process_slicing_task(slice_requested_event_json)

    mock_publish.assert_called_once()
    queue, event = mock_publish.call_args[0]
    assert queue == RESULTS_QUEUE
    assert isinstance(event, SliceFailedEvent)
    assert event.event_type == "slice.failed"
    assert event.payload.retryable is False
    assert "Orca slice failed" in event.payload.error_message


@patch("src.core.processor.MinioClient")
@patch("src.core.processor.get_settings")
def test_process_slicing_task_invalid_payload_raises(
    mock_get_settings,
    _mock_minio_cls,
) -> None:
    mock_get_settings.return_value = MagicMock()

    with pytest.raises(ValidationError):
        process_slicing_task("{not json")
