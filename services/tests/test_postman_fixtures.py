import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("profile_id", [3, 4, 5])
def test_postman_fixtures_include_filament_density(profile_id: int) -> None:
    fixture_path = (
        REPO_ROOT / "tests" / "postman" / "fixtures" / "profiles" / str(profile_id) / "filament.json"
    )
    data = json.loads(fixture_path.read_text())

    assert "filament_density" in data
    assert float(data["filament_density"][0]) > 0
