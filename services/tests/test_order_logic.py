import json
import importlib.util
from pathlib import Path
import sys
import os
import types
import io
import pytest
import uuid
from fastapi.testclient import TestClient

ORDER_SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../order-service"))
ORDER_MAIN_PATH = Path(ORDER_SERVICE_DIR) / "main.py"


def _reset_order_modules() -> None:
    for module_name in (
        "core",
        "core.database",
        "core.calculator",
        "core.stock",
        "core.order_manager",
        "main",
    ):
        sys.modules.pop(module_name, None)


def _install_order_package() -> None:
    package = types.ModuleType("core")
    package.__path__ = [os.path.join(ORDER_SERVICE_DIR, "core")]
    sys.modules["core"] = package


def _load_order_main():
    _reset_order_modules()
    _install_order_package()
    spec = importlib.util.spec_from_file_location("order_service_main", ORDER_MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["order_service_main"] = module
    spec.loader.exec_module(module)
    return module


class _DummyMinioObject:
    def __init__(self, data: bytes):
        self._data = data
        self.closed = False
        self.released = False

    def stream(self, amt: int = 65536):
        for idx in range(0, len(self._data), amt):
            yield self._data[idx : idx + amt]

    def close(self):
        self.closed = True

    def release_conn(self):
        self.released = True


sys.path.insert(0, ORDER_SERVICE_DIR)

_reset_order_modules()
_install_order_package()

from core.order_manager import OrderManager, OrderStatus, InvalidStatusTransitionError


class TestOrderManager:
    def setup_method(self):
        _reset_order_modules()
        _install_order_package()
        from core.database import db_stub

        db_stub.reset_stub()
        self.manager = OrderManager()
        self.file_data = self.manager.save_file("test.stl", 1024)
        self.file_id = self.file_data["fileId"]
        self.profile_id = 3

    def test_create_order(self):
        order = self.manager.create_order(self.file_id, self.profile_id)

        assert order["status"] == OrderStatus.PENDING.value
        assert order["fileId"] == self.file_id
        assert order["profileId"] == self.profile_id

    def test_get_nonexistent_order(self):
        with pytest.raises(KeyError, match="не найден"):
            self.manager.get_order(str(uuid.uuid4()))

    def test_valid_status_transition(self):
        order = self.manager.create_order(self.file_id, self.profile_id)
        order_id = order["orderId"]

        # PENDING -> SLICING
        self.manager.update_status(order_id, "slicing")
        assert self.manager.get_order(order_id)["status"] == OrderStatus.SLICING.value

        # SLICING -> PRICED
        self.manager.update_status(order_id, "priced")
        assert self.manager.get_order(order_id)["status"] == OrderStatus.PRICED.value

    def test_invalid_status_transition(self):
        order = self.manager.create_order(self.file_id, self.profile_id)
        order_id = order["orderId"]

        # PENDING -> PRINTING (нельзя пропустить slicing/priced)
        with pytest.raises(
            InvalidStatusTransitionError, match="Невозможно изменить статус"
        ):
            self.manager.update_status(order_id, "printing")

    def test_invalid_status_value(self):
        order = self.manager.create_order(self.file_id, self.profile_id)
        order_id = order["orderId"]

        with pytest.raises(ValueError, match="Неизвестный статус"):
            self.manager.update_status(order_id, "unknown_status_123")

    def test_slicing_result_reserve_failure_marks_order_failed(self, monkeypatch):
        order = self.manager.create_order(self.file_id, self.profile_id)
        order_id = order["orderId"]
        self.manager.update_status(order_id, OrderStatus.SLICING.value)

        order_main = _load_order_main()

        class FailedReserveResponse:
            status_code = 500
            text = "reservations_amount_check"

            @staticmethod
            def json():
                return {}

        monkeypatch.setattr(order_main, "order_db", self.manager)
        monkeypatch.setattr(
            order_main.httpx,
            "post",
            lambda *args, **kwargs: FailedReserveResponse(),
        )

        order_main.handle_slicing_result(
            json.dumps(
                {
                    "event_type": "slice.completed",
                    "payload": {
                        "order_id": order_id,
                        "filament_weight_g": 0.001,
                        "print_time_sec": 1,
                    },
                }
            )
        )

        stored = self.manager.get_order(order_id)
        assert stored["status"] == OrderStatus.FAILED.value
        assert stored["slicingResult"] is None
        assert "Inventory reserve failed with 500" in stored["errorMessage"]

    def test_slicing_result_stores_gcode_object_key(self, monkeypatch):
        order = self.manager.create_order(self.file_id, self.profile_id)
        order_id = order["orderId"]
        self.manager.update_status(order_id, OrderStatus.SLICING.value)

        order_main = _load_order_main()

        class ReserveOkResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"price": {"amount": "12.34", "currency": "RUB"}}

        monkeypatch.setattr(order_main, "order_db", self.manager)
        monkeypatch.setattr(
            order_main.httpx,
            "post",
            lambda *args, **kwargs: ReserveOkResponse(),
        )

        order_main.handle_slicing_result(
            json.dumps(
                {
                    "event_type": "slice.completed",
                    "payload": {
                        "order_id": order_id,
                        "filament_weight_g": 5.5,
                        "print_time_sec": 42,
                        "gcode_object_key": f"gcode/orders/{order_id}/result.gcode",
                    },
                }
            )
        )

        stored = self.manager.get_order(order_id)
        assert stored["status"] == OrderStatus.PRICED.value
        assert stored["slicingResult"]["gcodeObjectKey"] == f"gcode/orders/{order_id}/result.gcode"


class TestOrderDownloadEndpoint:
    def setup_method(self):
        _reset_order_modules()
        _install_order_package()
        from core.database import db_stub

        db_stub.reset_stub()
        self.manager = OrderManager()
        file_record = self.manager.save_file("widget.stl", 1024)
        self.file_id = file_record["fileId"]
        self.order = self.manager.create_order(
            self.file_id,
            3,
            api_key_identity="user-0001",
        )
        self.order_id = self.order["orderId"]
        self.manager.update_status(self.order_id, OrderStatus.SLICING.value)
        self.manager.update_status(
            self.order_id,
            OrderStatus.PRICED.value,
            slicing_result={
                "weightGrams": 4.2,
                "printTimeSeconds": 60,
                "price": {"amount": "1.23", "currency": "RUB"},
                "gcodeObjectKey": f"gcode/orders/{self.order_id}/result.gcode",
            },
        )

    def test_download_gcode_success(self, monkeypatch):
        order_main = _load_order_main()
        monkeypatch.setattr(order_main, "order_db", self.manager)

        dummy_object = _DummyMinioObject(b"G1 X1 Y1\n")
        order_id = self.order_id

        class FakeMinioClient:
            def __init__(self, _settings):
                pass

            def stat_object(self, object_key: str):
                assert object_key == f"gcode/orders/{order_id}/result.gcode"
                return object()

            def get_object(self, object_key: str):
                assert object_key == f"gcode/orders/{order_id}/result.gcode"
                return dummy_object

        monkeypatch.setattr(order_main, "OrderMinioClient", FakeMinioClient)

        client = TestClient(order_main.app)
        response = client.get(
            f"/api/orders/{self.order_id}/download",
            headers={"X-API-Key": "demo-api-key"},
        )

        assert response.status_code == 200
        assert response.content == b"G1 X1 Y1\n"
        assert response.headers["content-type"].startswith("application/octet-stream")
        assert "attachment;" in response.headers["content-disposition"]
        assert "widget.gcode" in response.headers["content-disposition"]
        assert dummy_object.closed is True
        assert dummy_object.released is True

    def test_download_gcode_forbidden_for_other_api_key(self, monkeypatch):
        order_main = _load_order_main()
        monkeypatch.setattr(order_main, "order_db", self.manager)

        client = TestClient(order_main.app)
        response = client.get(
            f"/api/orders/{self.order_id}/download",
            headers={"X-API-Key": "sample-api-key"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    def test_download_gcode_not_ready(self, monkeypatch):
        order_main = _load_order_main()
        monkeypatch.setattr(order_main, "order_db", self.manager)
        second_file = self.manager.save_file("draft.stl", 256)
        second_order = self.manager.create_order(
            second_file["fileId"],
            3,
            api_key_identity="user-0001",
        )

        client = TestClient(order_main.app)
        response = client.get(
            f"/api/orders/{second_order['orderId']}/download",
            headers={"X-API-Key": "demo-api-key"},
        )

        assert response.status_code == 409
        assert response.json()["code"] == "GCODE_NOT_READY"
