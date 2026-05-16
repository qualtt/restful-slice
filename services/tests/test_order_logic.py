import json
import sys
import os
import pytest
import uuid

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../order-service"))
)

if "core" in sys.modules:
    del sys.modules["core"]
if "core.calculator" in sys.modules:
    del sys.modules["core.calculator"]
if "core.stock" in sys.modules:
    del sys.modules["core.stock"]

from core.order_manager import OrderManager, OrderStatus, InvalidStatusTransitionError


class TestOrderManager:
    def setup_method(self):
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
        import main as order_main

        order = self.manager.create_order(self.file_id, self.profile_id)
        order_id = order["orderId"]
        self.manager.update_status(order_id, OrderStatus.SLICING.value)

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
