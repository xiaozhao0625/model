from __future__ import annotations

import sqlite3

from ai_screenshot_platform.master.models.entities import AppRecord


class AppRepo:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, record: AppRecord) -> AppRecord:
        self.connection.execute(
            "INSERT INTO apps (app_id, name, type, platform) VALUES (?, ?, ?, ?)",
            (record.app_id, record.name, record.type, record.platform),
        )
        self.connection.commit()
        return record

    def list(self) -> list[AppRecord]:
        rows = self.connection.execute(
            "SELECT app_id, name, type, platform FROM apps ORDER BY app_id"
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, app_id: str) -> AppRecord | None:
        row = self.connection.execute(
            "SELECT app_id, name, type, platform FROM apps WHERE app_id = ?",
            (app_id,),
        ).fetchone()
        return self._from_row(row) if row is not None else None

    def _from_row(self, row: sqlite3.Row) -> AppRecord:
        return AppRecord(
            app_id=str(row["app_id"]),
            name=str(row["name"]),
            type=str(row["type"]),
            platform=str(row["platform"]),
        )
