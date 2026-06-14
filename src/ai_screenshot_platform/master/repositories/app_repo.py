from __future__ import annotations

import sqlite3

from ai_screenshot_platform.master.models.entities import AppRecord


class AppRepo:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._columns = self._load_columns()
        self._has_created_at = "created_at" in self._columns

    def create(self, record: AppRecord) -> AppRecord:
        self.connection.execute(
            "INSERT INTO apps (app_id, name, type, platform) VALUES (?, ?, ?, ?)",
            (record.app_id, record.name, record.type, record.platform),
        )
        self.connection.commit()
        created = self.get(record.app_id)
        if created is None:
            raise KeyError(f"app not found after create: {record.app_id}")
        return created

    def list(self) -> list[AppRecord]:
        rows = self.connection.execute(
            f"SELECT {self._select_columns()} FROM apps ORDER BY app_id"
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, app_id: str) -> AppRecord | None:
        row = self.connection.execute(
            f"SELECT {self._select_columns()} FROM apps WHERE app_id = ?",
            (app_id,),
        ).fetchone()
        return self._from_row(row) if row is not None else None

    def _load_columns(self) -> set[str]:
        if self.connection.__class__.__name__ == "PostgresConnectionAdapter":
            rows = self.connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'apps'
                """
            ).fetchall()
            return {str(row["column_name"]) for row in rows}
        rows = self.connection.execute("PRAGMA table_info(apps)").fetchall()
        return {str(row["name"]) for row in rows}

    def _select_columns(self) -> str:
        columns = ["app_id", "name", "type", "platform"]
        if self._has_created_at:
            columns.append("created_at")
        return ", ".join(columns)

    def _from_row(self, row: sqlite3.Row) -> AppRecord:
        return AppRecord(
            app_id=str(row["app_id"]),
            name=str(row["name"]),
            type=str(row["type"]),
            platform=str(row["platform"]),
            created_at=str(row["created_at"]) if self._has_created_at and row["created_at"] else None,
            backend_source="database",
        )
