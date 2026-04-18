from uuid import uuid4

class InsufficientStockError(ValueError):
    pass

class InventoryStock:
    def __init__(self):
        from core.database import db_stub
        self.db = db_stub

    def get_stock(self, material_id: int) -> float:
        # SELECT total_grams FROM inventory WHERE id = material_id
        record = self.db.select("inventory", str(material_id))
        return record.get("total_grams", 0.0) if record else 0.0

    def get_available(self, material_id: int) -> float:
        total = self.get_stock(material_id)
        # SELECT amount FROM reservations WHERE material_id = ...
        reservations = self.db.select_all("reservations")
        reserved = sum(res["amount"] for res in reservations if res["material_id"] == material_id)
        return total - reserved

    def add_material(self, material_id: int, amount_grams: float) -> float:
        if amount_grams <= 0:
            raise ValueError("Количество пополнения должно быть больше нуля")
            
        current = self.get_stock(material_id)
        new_total = round(current + amount_grams, 2)
        
        # INSERT OR UPDATE inventory
        if self.db.select("inventory", str(material_id)):
            self.db.update("inventory", str(material_id), {"total_grams": new_total})
        else:
            self.db.insert("inventory", str(material_id), {
                "material_id": material_id, 
                "total_grams": new_total
            })
            
        return new_total

    def reserve_material(self, order_id: str, material_id: int, amount_grams: float) -> str:
        if amount_grams <= 0:
            raise ValueError("Количество для резерва должно быть больше нуля")
            
        available = self.get_available(material_id)
        if available < amount_grams:
            raise InsufficientStockError(
                f"Only {available}g available, but {amount_grams}g requested"
            )
            
        res_id = str(uuid4())
        
        # INSERT INTO reservations
        self.db.insert("reservations", order_id, {
            "order_id": order_id,
            "reservation_id": res_id,
            "material_id": material_id,
            "amount": amount_grams
        })
        return res_id

    def confirm_reservation(self, order_id: str):
        res = self.db.select("reservations", order_id)
        if not res:
            raise KeyError(f"Резерв для заказа {order_id} не найден")
            
        # UPDATE inventory SET total_grams = total_grams - res.amount
        mat_id_str = str(res["material_id"])
        current_stock = self.get_stock(res["material_id"])
        self.db.update("inventory", mat_id_str, {"total_grams": round(current_stock - res["amount"], 2)})
        
        # DELETE FROM reservations
        self.db.delete("reservations", order_id)

    def cancel_reservation(self, order_id: str):
        if not self.db.select("reservations", order_id):
            raise KeyError(f"Резерв для заказа {order_id} не найден")
            
        # DELETE FROM reservations
        self.db.delete("reservations", order_id)
