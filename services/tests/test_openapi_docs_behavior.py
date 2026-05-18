import importlib
import importlib.util
import os
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[2]
ORDER_SERVICE_DIR = ROOT_DIR / "services" / "order-service"
ORDER_MAIN_PATH = ORDER_SERVICE_DIR / "main.py"
INVENTORY_SERVICE_DIR = ROOT_DIR / "services" / "inventory-service"


def _reset_order_modules() -> None:
    for module_name in (
        "core",
        "core.database",
        "core.calculator",
        "core.stock",
        "core.order_manager",
        "core.config",
        "core.minio_client",
        "core.rabbit_client",
        "main",
        "order_service_main",
    ):
        sys.modules.pop(module_name, None)


def _install_order_package() -> None:
    package = types.ModuleType("core")
    package.__path__ = [str(ORDER_SERVICE_DIR / "core")]
    sys.modules["core"] = package


def load_order_app():
    _reset_order_modules()
    _install_order_package()
    spec = importlib.util.spec_from_file_location("order_service_main", ORDER_MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["order_service_main"] = module
    spec.loader.exec_module(module)
    return module


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
    package.__path__ = [str(INVENTORY_SERVICE_DIR / "core")]
    sys.modules["core"] = package


class FakeInventoryDB:
    def __init__(self):
        self.inventory = {}
        self.reservations = {}

    def select(self, table: str, record_id: str):
        if table == "inventory":
            return self.inventory.get(int(record_id))
        if table == "reservations":
            return self.reservations.get(record_id)
        raise ValueError(f"Unsupported table: {table}")

    def insert(self, table: str, record_id: str, data: dict):
        if table == "inventory":
            self.inventory[int(record_id)] = {
                "material_id": int(record_id),
                "total_grams": float(data["total_grams"]),
            }
            return
        if table == "reservations":
            self.reservations[record_id] = {
                "order_id": record_id,
                "reservation_id": data["reservation_id"],
                "material_id": int(data["material_id"]),
                "amount": float(data["amount"]),
            }
            return
        raise ValueError(f"Unsupported table: {table}")

    def select_all(self, table: str):
        if table == "inventory":
            return list(self.inventory.values())
        if table == "reservations":
            return list(self.reservations.values())
        raise ValueError(f"Unsupported table: {table}")

    def update(self, table: str, record_id: str, updates: dict):
        if table == "inventory":
            self.inventory[int(record_id)]["total_grams"] = float(updates["total_grams"])
            return
        if table == "reservations":
            self.reservations[record_id].update(updates)
            return
        raise ValueError(f"Unsupported table: {table}")

    def delete(self, table: str, record_id: str):
        if table == "inventory":
            self.inventory.pop(int(record_id), None)
            return
        if table == "reservations":
            self.reservations.pop(record_id, None)
            return
        raise ValueError(f"Unsupported table: {table}")


def load_inventory_app():
    sys.path.insert(0, str(INVENTORY_SERVICE_DIR))
    _reset_inventory_modules()
    fake_database_module = types.ModuleType("core.database")
    fake_database_module.db_stub = FakeInventoryDB()
    sys.modules["core.database"] = fake_database_module
    _install_inventory_package()
    sys.modules.pop("main", None)
    return importlib.import_module("main")


def test_order_openapi_includes_api_key_security_and_examples():
    order_main = load_order_app()

    schema = order_main.app.openapi()

    assert schema["components"]["securitySchemes"]["APIKeyHeader"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }
    assert schema["paths"]["/api/orders"]["post"]["security"] == [{"APIKeyHeader": []}]
    request_schema = schema["components"]["schemas"]["CreateOrderRequest"]
    assert request_schema["example"]["profileId"] == 3
    params = schema["paths"]["/api/orders"]["get"]["parameters"]
    page_param = next(param for param in params if param["name"] == "page")
    assert page_param["schema"]["default"] == 1


def test_order_docs_preauthorize_default_api_key():
    order_main = load_order_app()
    client = TestClient(order_main.app)

    response = client.get("/api/orders/docs")

    assert response.status_code == 200
    body = response.text
    assert "/api/orders/docs-assets/swagger-ui/swagger-ui.css" in body
    assert "/api/orders/docs-assets/swagger-ui/swagger-ui-bundle.js" in body
    assert "/api/orders/docs-assets/swagger-ui/docs-bootstrap.js" in body
    assert "cdn.jsdelivr.net" not in body
    assert 'data-default-api-key="demo-api-key"' in body


def test_inventory_openapi_includes_api_key_security_and_examples():
    inventory_main = load_inventory_app()

    schema = inventory_main.app.openapi()

    assert schema["components"]["securitySchemes"]["APIKeyHeader"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }
    assert schema["paths"]["/api/inventory/profiles"]["get"]["security"] == [
        {"APIKeyHeader": []}
    ]
    reserve_schema = schema["components"]["schemas"]["ReserveRequest"]
    assert reserve_schema["example"]["profileId"] == 3
    params = schema["paths"]["/api/inventory/materials"]["get"]["parameters"]
    type_param = next(param for param in params if param["name"] == "type")
    assert type_param["schema"]["anyOf"][0]["type"] == "string"


def test_inventory_docs_preauthorize_default_api_key():
    inventory_main = load_inventory_app()
    client = TestClient(inventory_main.app)

    response = client.get("/api/inventory/docs")

    assert response.status_code == 200
    body = response.text
    assert "/api/inventory/docs-assets/swagger-ui/swagger-ui.css" in body
    assert "/api/inventory/docs-assets/swagger-ui/swagger-ui-bundle.js" in body
    assert "/api/inventory/docs-assets/swagger-ui/docs-bootstrap.js" in body
    assert "cdn.jsdelivr.net" not in body
    assert 'data-default-api-key="demo-api-key"' in body
