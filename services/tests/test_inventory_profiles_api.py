import importlib
import os
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[2]
INVENTORY_SERVICE_DIR = ROOT_DIR / "services" / "inventory-service"


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

    fake_database_module = types.ModuleType("core.database")
    fake_database_module.db_stub = FakeInventoryDB()
    sys.modules["core.database"] = fake_database_module
    sys.modules.pop("main", None)

    return importlib.import_module("main")


def test_inventory_profiles_include_standard_draft_and_high_quality():
    inventory_main = load_inventory_app()
    client = TestClient(inventory_main.app)

    response = client.get("/api/inventory/profiles?page=1&pageSize=20")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 3

    profiles = {profile["profileId"]: profile for profile in body["data"]}
    assert set(profiles) == {3, 4, 5}
    assert profiles[3]["process"]["name"] == "0.20mm Standard"
    assert profiles[4]["process"]["name"] == "0.24mm Draft"
    assert profiles[5]["process"]["name"] == "0.12mm Fine"


def test_inventory_profile_detail_for_high_quality():
    inventory_main = load_inventory_app()
    client = TestClient(inventory_main.app)

    response = client.get("/api/inventory/profiles/5")

    assert response.status_code == 200
    body = response.json()
    assert body["displayName"] == "PETG Высокое качество (K1C)"
    assert body["process"]["orcaProcessId"] == "0.12mm_fine_creality_k1c_0.4_nozzle"
    assert body["material"]["materialType"] == "PETG"


def test_inventory_health_ready():
    inventory_main = load_inventory_app()
    client = TestClient(inventory_main.app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
