import os
from typing import Any

import psycopg
from psycopg.rows import dict_row


class PostgresDB:
    def __init__(self):
        self.user = os.getenv("INV_DB_USER", "inv_admin")
        self.password = os.getenv("INV_DB_PASSWORD", "inv_pass")
        self.db_name = os.getenv("INV_DB_NAME", "inventory_db")
        self.host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5434"))
        self.url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"

    def _connect(self):
        return psycopg.connect(self.url, autocommit=True, row_factory=dict_row)

    def insert(self, table: str, record_id: str, data: dict[str, Any]):
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table == "inventory":
                    cur.execute(
                        """
                        INSERT INTO inventory (material_id, total_grams)
                        VALUES (%s, %s)
                        ON CONFLICT (material_id) DO UPDATE
                        SET total_grams = EXCLUDED.total_grams
                        """,
                        (int(record_id), float(data["total_grams"])),
                    )
                    return

                if table == "reservations":
                    cur.execute(
                        """
                        INSERT INTO reservations (order_id, reservation_id, material_id, amount)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (order_id) DO UPDATE
                        SET reservation_id = EXCLUDED.reservation_id,
                            material_id = EXCLUDED.material_id,
                            amount = EXCLUDED.amount
                        """,
                        (
                            record_id,
                            data["reservation_id"],
                            int(data["material_id"]),
                            float(data["amount"]),
                        ),
                    )
                    return

                raise ValueError(f"Unsupported table: {table}")

    def select(self, table: str, record_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table == "inventory":
                    cur.execute(
                        "SELECT material_id, total_grams FROM inventory WHERE material_id = %s",
                        (int(record_id),),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {
                        "material_id": row["material_id"],
                        "total_grams": float(row["total_grams"]),
                    }

                if table == "reservations":
                    cur.execute(
                        "SELECT order_id, reservation_id, material_id, amount FROM reservations WHERE order_id = %s",
                        (record_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {
                        "order_id": row["order_id"],
                        "reservation_id": str(row["reservation_id"]),
                        "material_id": row["material_id"],
                        "amount": float(row["amount"]),
                    }

                raise ValueError(f"Unsupported table: {table}")

    def select_all(self, table: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table == "inventory":
                    cur.execute(
                        "SELECT material_id, total_grams FROM inventory ORDER BY material_id"
                    )
                    return [
                        {
                            "material_id": row["material_id"],
                            "total_grams": float(row["total_grams"]),
                        }
                        for row in cur.fetchall()
                    ]

                if table == "reservations":
                    cur.execute(
                        "SELECT order_id, reservation_id, material_id, amount FROM reservations"
                    )
                    return [
                        {
                            "order_id": row["order_id"],
                            "reservation_id": str(row["reservation_id"]),
                            "material_id": row["material_id"],
                            "amount": float(row["amount"]),
                        }
                        for row in cur.fetchall()
                    ]

                raise ValueError(f"Unsupported table: {table}")

    def update(self, table: str, record_id: str, updates: dict[str, Any]):
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table == "inventory":
                    if "total_grams" in updates:
                        cur.execute(
                            "UPDATE inventory SET total_grams = %s WHERE material_id = %s",
                            (float(updates["total_grams"]), int(record_id)),
                        )
                    return

                if table == "reservations":
                    set_parts: list[str] = []
                    values: list[Any] = []
                    if "reservation_id" in updates:
                        set_parts.append("reservation_id = %s")
                        values.append(updates["reservation_id"])
                    if "material_id" in updates:
                        set_parts.append("material_id = %s")
                        values.append(int(updates["material_id"]))
                    if "amount" in updates:
                        set_parts.append("amount = %s")
                        values.append(float(updates["amount"]))

                    if set_parts:
                        values.append(record_id)
                    from psycopg import sql
                    
                    query = sql.SQL("UPDATE reservations SET {set_clause} WHERE order_id = {order_id}").format(
                        set_clause=sql.SQL(", ").join(
                            sql.SQL("{} = {}").format(sql.Identifier(col.split(" = ")[0]), sql.Placeholder())
                            for col in set_parts
                        ),
                        order_id=sql.Placeholder()
                    )
                    cur.execute(query, tuple(values))
                    return

                raise ValueError(f"Unsupported table: {table}")

    def delete(self, table: str, record_id: str):
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table == "reservations":
                    cur.execute(
                        "DELETE FROM reservations WHERE order_id = %s", (record_id,)
                    )
                    return
                if table == "inventory":
                    cur.execute(
                        "DELETE FROM inventory WHERE material_id = %s",
                        (int(record_id),),
                    )
                    return
                raise ValueError(f"Unsupported table: {table}")

    def _ensure_schema(self, cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                material_id INTEGER PRIMARY KEY,
                total_grams NUMERIC(12,2) NOT NULL CHECK (total_grams >= 0)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                order_id TEXT PRIMARY KEY,
                reservation_id UUID NOT NULL,
                material_id INTEGER NOT NULL REFERENCES inventory(material_id) ON DELETE RESTRICT,
                amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

    def reset_stub(self):
        # Kept for test compatibility.
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_schema(cur)
                cur.execute("TRUNCATE TABLE inventory CASCADE")


# Alias name kept to avoid touching all imports at once.
db_stub = PostgresDB()
