import json
from uuid import UUID

import pytest


@pytest.fixture
def slice_requested_event_dict() -> dict:
    return {
        "event_id": "11111111-1111-1111-1111-111111111111",
        "event_type": "slice.requested",
        "created_at": "2025-01-15T12:00:00+00:00",
        "source": "order-service",
        "spec_version": "1.0.0",
        "payload": {
            "order_id": "22222222-2222-2222-2222-222222222222",
            "customer_id": "33333333-3333-3333-3333-333333333333",
            "priority": "normal",
            "minio_paths": {
                "stl_file": "stl/orders/22222222/model.stl",
                "printer_profile": "profiles/printers/prusa_mk3s.json",
                "process_profile": "profiles/process/0_20mm_quality.json",
                "filament_profile": "profiles/filaments/generic_pla.json",
            },
        },
    }


@pytest.fixture
def slice_requested_event_json(slice_requested_event_dict: dict) -> str:
    return json.dumps(slice_requested_event_dict)


@pytest.fixture
def order_id() -> UUID:
    return UUID("22222222-2222-2222-2222-222222222222")
