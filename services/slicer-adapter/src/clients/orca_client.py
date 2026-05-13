import os
from typing import BinaryIO, Protocol

import requests

class _SettingsLike(Protocol):
    orca_api_url: str


def _body_looks_like_gcode(body: bytes) -> bool:
    """Heuristic: G-code is text with ; comments and/or G/M command lines (Orca export)."""
    if not body:
        return False
    head = body[:8192].lstrip()
    if not head:
        return False
    try:
        text = head.decode("utf-8")
    except UnicodeDecodeError:
        text = head.decode("latin-1", errors="replace")
    for line in text.splitlines()[:80]:
        s = line.strip()
        if not s:
            continue
        if s.startswith(";"):
            return True
        if len(s) >= 2 and s[0] in "GM" and (s[1].isdigit() or s[1] in ".*"):
            return True
    return False


class OrcaSlicerClient:
    def __init__(self, settings: _SettingsLike) -> None:
        self._base = settings.orca_api_url.rstrip("/")

    def slice_model(
        self,
        stl_path: str,
        profile_paths: dict[str, str],
        timeout: int = 600,
    ) -> tuple[str, dict]:
        url = f"{self._base}/slice"
        opened: list[BinaryIO] = []
        try:
            stl_fh = open(stl_path, "rb")
            opened.append(stl_fh)
            files: list[tuple[str, tuple[str, BinaryIO, str]]] = [
                (
                    "file",
                    (os.path.basename(stl_path), stl_fh, "application/octet-stream"),
                )
            ]
            for field_name, path in profile_paths.items():
                fh = open(path, "rb")
                opened.append(fh)
                files.append(
                    (field_name, (os.path.basename(path), fh, "application/json"))
                )
            resp = requests.post(url, files=files, data={}, timeout=timeout)
        finally:
            for fh in opened:
                fh.close()

        if not resp.ok:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            raise RuntimeError(f"Orca slice failed ({resp.status_code}): {detail}")

        metadata: dict[str, object] = {}
        if resp.headers.get("X-Print-Time-Seconds"):
            metadata["print_time_sec"] = int(resp.headers["X-Print-Time-Seconds"])
        if resp.headers.get("X-Filament-Used-g"):
            metadata["filament_weight_g"] = float(resp.headers["X-Filament-Used-g"])
        if resp.headers.get("X-Filament-Used-mm"):
            metadata["filament_length_mm"] = float(resp.headers["X-Filament-Used-mm"])
        if resp.headers.get("X-Slicer-Version"):
            metadata["slicer_version"] = resp.headers["X-Slicer-Version"]

        out_dir = os.path.dirname(stl_path)
        gcode_path = os.path.join(out_dir, "result.gcode")
        raw = resp.content
        if len(raw) >= 2 and raw[:2] == b"PK":
            raise RuntimeError(
                "Slicer returned a ZIP archive; single G-code export is required"
            )
        if not raw:
            raise RuntimeError("Slicer returned an empty response body")
        if not _body_looks_like_gcode(raw):
            raise RuntimeError("Slicer response does not look like G-code")

        with open(gcode_path, "wb") as f:
            f.write(raw)

        return gcode_path, metadata
