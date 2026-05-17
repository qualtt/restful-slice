import sys
import os

from fastapi.testclient import TestClient

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../order-service"))
)

if "core" in sys.modules:
    del sys.modules["core"]
if "core.database" in sys.modules:
    del sys.modules["core.database"]


def load_order_app():
    sys.modules.pop("main", None)
    import main as order_main

    return order_main


def test_order_health_ready():
    order_main = load_order_app()
    client = TestClient(order_main.app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
