import os
import tempfile
from types import SimpleNamespace

import pytest

from src.clients.orca_client import OrcaSlicerClient


@pytest.mark.skipif(
    os.environ.get("RUN_ORCA_SMOKE") != "1",
    reason="Set RUN_ORCA_SMOKE=1 to run against a real Orca Slicer API",
)
def test_orca_api_smoke_reachable() -> None:
    """
    Smoke test that verifies the adapter code can talk to a real Orca Slicer API.

    It does NOT require a successful slice (that would need real STL + valid profiles).
    The test passes if we get any HTTP response from /slice and our client turns it into a
    structured RuntimeError (i.e. not a connection/timeout error).
    """

    base_url = os.environ.get("ORCA_API_URL", "http://localhost:3000")
    settings = SimpleNamespace(orca_api_url=base_url)
    client = OrcaSlicerClient(settings)  # type: ignore[arg-type]

    with tempfile.TemporaryDirectory() as d:
        stl_path = os.path.join(d, "dummy.stl")
        printer_path = os.path.join(d, "printer.json")
        preset_path = os.path.join(d, "process.json")
        filament_path = os.path.join(d, "filament.json")

        # Minimal placeholders: the server should respond with 4xx/5xx, proving reachability.
        with open(stl_path, "wb") as f:
            f.write(b"solid dummy\nendsolid dummy\n")
        for p in (printer_path, preset_path, filament_path):
            with open(p, "wb") as f:
                f.write(b"{}")ы

        profile_paths = {
            "printerProfile": printer_path,
            "presetProfile": preset_path,
            "filamentProfile": filament_path,
        }

        try:
            gcode_path, meta = client.slice_model(stl_path, profile_paths, timeout=15)
        except RuntimeError as exc:
            # If we got an HTTP response, OrcaSlicerClient raises RuntimeError with status code.
            # Connection errors typically surface as requests exceptions (not RuntimeError here).
            msg = str(exc)
            assert "Orca slice failed (" in msg or "Slicer returned" in msg
            return

        # If it unexpectedly succeeded, assert it produced output on disk.
        assert os.path.exists(gcode_path)
        assert isinstance(meta, dict)
