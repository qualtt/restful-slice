from unittest.mock import MagicMock, patch

import requests

from src.clients.orca_client import OrcaSlicerClient


def _settings() -> MagicMock:
    return MagicMock(orca_api_url="http://orca:3000")


@patch("src.clients.orca_client.requests.post")
@patch("src.clients.orca_client.open")
def test_slice_model_uses_orca_message_field_for_non_2xx(
    mock_open,
    mock_post,
) -> None:
    mock_open.return_value = MagicMock()
    response = MagicMock(spec=requests.Response)
    response.ok = False
    response.status_code = 500
    response.json.return_value = {
        "message": "Slicing failed with error from slicer: non-manifold geometry detected"
    }
    mock_post.return_value = response

    client = OrcaSlicerClient(_settings())

    try:
        client.slice_model(
            "/tmp/model.stl",
            {
                "printerProfile": "/tmp/printer.json",
                "presetProfile": "/tmp/process.json",
                "filamentProfile": "/tmp/filament.json",
            },
        )
    except RuntimeError as exc:
        assert (
            str(exc)
            == "Orca slice failed (500): Slicing failed with error from slicer: non-manifold geometry detected"
        )
    else:
        raise AssertionError("Expected RuntimeError")


@patch("src.clients.orca_client.requests.post")
@patch("src.clients.orca_client.open")
def test_slice_model_preserves_local_validation_errors_after_successful_response(
    mock_open,
    mock_post,
) -> None:
    mock_open.return_value = MagicMock()
    response = MagicMock(spec=requests.Response)
    response.ok = True
    response.headers = {}
    response.content = b"\x00\x01\x02not gcode"
    mock_post.return_value = response

    client = OrcaSlicerClient(_settings())

    try:
        client.slice_model(
            "/tmp/model.stl",
            {
                "printerProfile": "/tmp/printer.json",
                "presetProfile": "/tmp/process.json",
                "filamentProfile": "/tmp/filament.json",
            },
        )
    except RuntimeError as exc:
        assert str(exc) == "Slicer response does not look like G-code"
    else:
        raise AssertionError("Expected RuntimeError")
