import os
from pathlib import Path
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config
from psycopg.rows import dict_row
from psycopg.types.json import Json


class PostgresDB:
    def __init__(self):
        self.user = os.getenv("ORDER_DB_USER", "order_admin")
        self.password = os.getenv("ORDER_DB_PASSWORD", "order_pass")
        self.db_name = os.getenv("ORDER_DB_NAME", "orders_db")
        self.host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5434"))
        self.url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"

    def _connect(self):
        return psycopg.connect(self.url, autocommit=True, row_factory=dict_row)

    @staticmethod
    def _service_root() -> Path:
        return Path(__file__).resolve().parent.parent

    @classmethod
    def _alembic_config(cls) -> Config:
        service_root = cls._service_root()
        config = Config(str(service_root / "alembic.ini"))
        config.set_main_option("script_location", str(service_root / "alembic"))
        return config

    @staticmethod
    def _core_tables_exist(cur: psycopg.Cursor) -> bool:
        cur.execute(
            """
            SELECT
                to_regclass('public.files') IS NOT NULL AS files_exists,
                to_regclass('public.orders') IS NOT NULL AS orders_exists
            """
        )
        row = cur.fetchone()
        return bool(row and row["files_exists"] and row["orders_exists"])

    @classmethod
    def _apply_migrations(cls) -> None:
        command.upgrade(cls._alembic_config(), "head")

    @staticmethod
    def _map_order_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None

        return {
            "orderId": str(row["order_id"]),
            "status": row["status"],
            "fileId": str(row["file_id"]),
            "profileId": row["profile_id"],
            "slicingResult": row.get("slicing_result"),
            "errorMessage": row.get("error_message"),
            "createdAt": row["created_at"].isoformat(),
            "updatedAt": row["updated_at"].isoformat(),
        }

    @staticmethod
    def _map_file_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None

        return {
            "fileId": str(row["file_id"]),
            "filename": row["filename"],
            "sizeBytes": row["size_bytes"],
            "uploadedAt": row["uploaded_at"].isoformat(),
            "objectKey": row.get("object_key"),
        }

    def insert(self, table: str, record_id: str, data: dict[str, Any]):
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table == "telemetry_events":
                    cur.execute(
                        """
                        INSERT INTO telemetry_events (
                            id, session_id, event_name, route, consent_version, context, data, client_ts
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            record_id,
                            data["session_id"],
                            data["event_name"],
                            data["route"],
                            data["consent_version"],
                            Json(data["context"]),
                            Json(data["data"]),
                            data["client_ts"],
                        ),
                    )
                    return

                if table == "files":
                    cur.execute(
                        """
                        INSERT INTO files (file_id, filename, size_bytes, uploaded_at, object_key)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (file_id) DO UPDATE
                        SET filename = EXCLUDED.filename,
                            size_bytes = EXCLUDED.size_bytes,
                            uploaded_at = EXCLUDED.uploaded_at,
                            object_key = EXCLUDED.object_key
                        """,
                        (
                            record_id,
                            data["filename"],
                            data["sizeBytes"],
                            data["uploadedAt"],
                            data.get("objectKey"),
                        ),
                    )
                    return

                if table == "orders":
                    cur.execute(
                        """
                        INSERT INTO orders (
                            order_id, status, file_id, profile_id,
                            slicing_result, error_message, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (order_id) DO UPDATE
                        SET status = EXCLUDED.status,
                            file_id = EXCLUDED.file_id,
                            profile_id = EXCLUDED.profile_id,
                            slicing_result = EXCLUDED.slicing_result,
                            error_message = EXCLUDED.error_message,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            record_id,
                            data["status"],
                            data["fileId"],
                            data["profileId"],
                            Json(data["slicingResult"])
                            if data.get("slicingResult") is not None
                            else None,
                            data.get("errorMessage"),
                            data["createdAt"],
                            data["updatedAt"],
                        ),
                    )
                    return

                raise ValueError(f"Unsupported table: {table}")

    def select(self, table: str, record_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table == "files":
                    cur.execute(
                        "SELECT file_id, filename, size_bytes, uploaded_at, object_key FROM files WHERE file_id = %s",
                        (record_id,),
                    )
                    return self._map_file_row(cur.fetchone())

                if table == "orders":
                    cur.execute(
                        """
                        SELECT order_id, status, file_id, profile_id, slicing_result, error_message, created_at, updated_at
                        FROM orders
                        WHERE order_id = %s
                        """,
                        (record_id,),
                    )
                    return self._map_order_row(cur.fetchone())

                raise ValueError(f"Unsupported table: {table}")

    def select_all(self, table: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table == "orders":
                    cur.execute(
                        """
                        SELECT order_id, status, file_id, profile_id, slicing_result, error_message, created_at, updated_at
                        FROM orders
                        ORDER BY created_at DESC
                        """
                    )
                    return [self._map_order_row(row) for row in cur.fetchall()]

                if table == "files":
                    cur.execute(
                        "SELECT file_id, filename, size_bytes, uploaded_at, object_key FROM files ORDER BY uploaded_at DESC"
                    )
                    return [self._map_file_row(row) for row in cur.fetchall()]

                raise ValueError(f"Unsupported table: {table}")

    def update(self, table: str, record_id: str, updates: dict[str, Any]):
        if table == "files":
            if "objectKey" in updates:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE files SET object_key = %s WHERE file_id = %s",
                            (updates["objectKey"], record_id),
                        )
            return

        if table != "orders":
            raise ValueError(f"Unsupported table for update: {table}")

        set_clauses: list[str] = []
        values: list[Any] = []

        mapping = {
            "status": "status",
            "profileId": "profile_id",
            "errorMessage": "error_message",
            "updatedAt": "updated_at",
        }

        for key, column in mapping.items():
            if key in updates:
                set_clauses.append(f"{column} = %s")
                values.append(updates[key])

        if "slicingResult" in updates:
            set_clauses.append("slicing_result = %s")
            values.append(
                Json(updates["slicingResult"])
                if updates["slicingResult"] is not None
                else None
            )

        if not set_clauses:
            return

        values.append(record_id)

        with self._connect() as conn:
            with conn.cursor() as cur:
                from psycopg import sql

                query = sql.SQL("UPDATE orders SET {set_clause} WHERE order_id = {order_id}").format(
                    set_clause=sql.SQL(", ").join(
                        sql.SQL("{} = {}").format(sql.Identifier(col.split(" = ")[0]), sql.Placeholder())
                        for col in set_clauses
                    ),
                    order_id=sql.Placeholder()
                )
                cur.execute(query, tuple(values))

    def delete(self, table: str, record_id: str):
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table == "orders":
                    cur.execute("DELETE FROM orders WHERE order_id = %s", (record_id,))
                    return
                if table == "files":
                    cur.execute("DELETE FROM files WHERE file_id = %s", (record_id,))
                    return
                raise ValueError(f"Unsupported table: {table}")

    def reset_stub(self):
        schema_ready = False
        with self._connect() as conn:
            with conn.cursor() as cur:
                schema_ready = self._core_tables_exist(cur)

        if not schema_ready:
            self._apply_migrations()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE orders, files RESTART IDENTITY CASCADE")


# Alias name kept to avoid touching all imports at once.
db_stub = PostgresDB()
