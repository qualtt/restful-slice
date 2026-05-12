from enum import Enum
from uuid import uuid4
from datetime import datetime, timezone


class OrderStatus(str, Enum):
    PENDING = "pending"
    SLICING = "slicing"
    PRICED = "priced"
    CONFIRMED = "confirmed"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InvalidStatusTransitionError(Exception):
    pass


class OrderManager:
    """Управление заказами и отслеживание статусов из процесса 3D-печати"""

    VALID_TRANSITIONS = {
        OrderStatus.PENDING: [
            OrderStatus.SLICING,
            OrderStatus.FAILED,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.SLICING: [
            OrderStatus.PRICED,
            OrderStatus.FAILED,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.PRICED: [
            OrderStatus.CONFIRMED,
            OrderStatus.FAILED,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.CONFIRMED: [OrderStatus.PRINTING, OrderStatus.FAILED],
        OrderStatus.PRINTING: [OrderStatus.COMPLETED, OrderStatus.FAILED],
        OrderStatus.COMPLETED: [],
        OrderStatus.FAILED: [],
        OrderStatus.CANCELLED: [],
    }

    def __init__(self):
        # Инициализируем соединение с "тестовой БД"
        from core.database import db_stub

        self.db = db_stub

    def save_file(self, filename: str, size_bytes: int) -> dict:
        file_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        file_data = {
            "fileId": file_id,
            "filename": filename,
            "sizeBytes": size_bytes,
            "uploadedAt": now,
        }
        # INSERT INTO files ...
        self.db.insert("files", file_id, file_data)
        return file_data

    def get_file(self, file_id: str) -> dict:
        # SELECT * FROM files WHERE id = ...
        return self.db.select("files", file_id)

    def create_order(self, file_id: str, profile_id: int) -> dict:
        if not self.get_file(file_id):
            raise KeyError(f"Файл с ID {file_id} не найден")

        order_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        order = {
            "orderId": order_id,
            "status": OrderStatus.PENDING.value,
            "fileId": file_id,
            "profileId": profile_id,
            "slicingResult": None,
            "errorMessage": None,
            "createdAt": now,
            "updatedAt": now,
        }
        # INSERT INTO orders ...
        self.db.insert("orders", order_id, order)
        return order

    def get_order(self, order_id: str) -> dict:
        order = self.db.select("orders", order_id)
        if not order:
            raise KeyError(f"Заказ с ID {order_id} не найден")
        return order

    def list_orders(self) -> list[dict]:
        return self.db.select_all("orders")

    def update_status(
        self,
        order_id: str,
        new_status: str,
        slicing_result: dict = None,
        error_message: str = None,
    ) -> dict:
        order = self.get_order(order_id)
        current_status = OrderStatus(order["status"])

        try:
            enum_status = OrderStatus(new_status)
        except ValueError:
            raise ValueError(f"Неизвестный статус: {new_status}")

        allowed = self.VALID_TRANSITIONS.get(current_status, [])
        if enum_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Невозможно изменить статус заказа с {current_status.value} на {enum_status.value}"
            )

        updates = {
            "status": enum_status.value,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        if slicing_result:
            updates["slicingResult"] = slicing_result
        if error_message:
            updates["errorMessage"] = error_message

        # UPDATE orders SET ... WHERE id = order_id
        self.db.update("orders", order_id, updates)
        return self.get_order(order_id)
