import sys
import os
import types
import pytest

INVENTORY_SERVICE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../inventory-service")
)


def _reset_inventory_modules() -> None:
    for module_name in (
        "core",
        "core.database",
        "core.stock",
        "core.calculator",
        "core.order_manager",
        "main",
    ):
        sys.modules.pop(module_name, None)


def _install_inventory_package() -> None:
    package = types.ModuleType("core")
    package.__path__ = [os.path.join(INVENTORY_SERVICE_DIR, "core")]
    sys.modules["core"] = package


sys.path.insert(0, INVENTORY_SERVICE_DIR)

_reset_inventory_modules()
_install_inventory_package()

from core.calculator import Calculator
from core.stock import InventoryStock, InsufficientStockError


class TestCostCalculator:
    def test_calculate_cost_standard(self):
        # 100g * 0.15 * 1.2
        cost = Calculator.calculate_cost(
            weight_grams=100.0, price_per_gram=0.15, markup_percent=1.2
        )
        assert cost == 18.0

    def test_calculate_cost_zero(self):
        cost = Calculator.calculate_cost(
            weight_grams=0.0, price_per_gram=5.0, markup_percent=1.5
        )
        assert cost == 0.0

    def test_calculate_cost_negative_values(self):
        with pytest.raises(ValueError, match="Вес не может быть отрицательным"):
            Calculator.calculate_cost(
                weight_grams=-10.0, price_per_gram=5.0, markup_percent=1.5
            )

        with pytest.raises(
            ValueError, match="Расценки/наценка не могут быть отрицательными"
        ):
            Calculator.calculate_cost(
                weight_grams=100.0, price_per_gram=-0.5, markup_percent=1.5
            )


class TestInventoryStock:
    def setup_method(self):
        _reset_inventory_modules()
        _install_inventory_package()
        from core.database import db_stub

        db_stub.reset_stub()
        self.stock = InventoryStock()

    def test_add_and_get_stock(self):
        self.stock.add_material(1, 1500.5)
        assert self.stock.get_stock(1) == 1500.5
        assert self.stock.get_available(1) == 1500.5

    def test_reserve_material_success(self):
        self.stock.add_material(1, 1000.0)
        self.stock.reserve_material("order-1", 1, 250.0)

        assert self.stock.get_available(1) == 750.0
        assert self.stock.get_stock(1) == 1000.0  # Stock itself hasn't changed yet

        # Now confirm it
        self.stock.confirm_reservation("order-1")
        assert self.stock.get_stock(1) == 750.0

    def test_reserve_tiny_material_uses_minimum_quantum(self):
        from core.database import db_stub

        self.stock.add_material(2, 1.0)
        self.stock.reserve_material("order-tiny", 2, 0.001)

        reservation = db_stub.select("reservations", "order-tiny")
        assert reservation["amount"] == 0.01
        assert self.stock.get_available(2) == 0.99

    def test_reserve_material_cancel(self):
        self.stock.add_material(2, 500.0)
        self.stock.reserve_material("order-2", 2, 100.0)
        assert self.stock.get_available(2) == 400.0

        self.stock.cancel_reservation("order-2")
        assert self.stock.get_available(2) == 500.0
        assert self.stock.get_stock(2) == 500.0

    def test_reserve_material_insufficient(self):
        self.stock.add_material(3, 100.0)

        with pytest.raises(InsufficientStockError):
            self.stock.reserve_material("order-3", 3, 200.0)

        assert self.stock.get_available(3) == 100.0

    def test_reserve_zero_or_negative(self):
        with pytest.raises(ValueError):
            self.stock.reserve_material("order-x", 1, -50.0)

        with pytest.raises(ValueError):
            self.stock.reserve_material("order-x", 1, 0)
