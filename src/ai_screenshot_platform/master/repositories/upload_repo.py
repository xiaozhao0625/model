from __future__ import annotations

import sqlite3

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.models.entities import UploadRecord


class UploadRepo:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert(self, record: UploadRecord) -> UploadRecord:
        self.connection.execute(
            """
            INSERT INTO uploads (upload_id, run_id, status)
            VALUES (?, ?, ?)
            ON CONFLICT(upload_id) DO UPDATE SET
                run_id = excluded.run_id,
                status = excluded.status
            """,
            (record.upload_id, record.run_id, record.status.value),
        )
        self.connection.commit()
        return record

    def get_by_run(self, run_id: str) -> UploadRecord | None:
        row = self.connection.execute(
            "SELECT upload_id, run_id, status FROM uploads WHERE run_id = ? ORDER BY upload_id DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return UploadRecord(
            upload_id=str(row["upload_id"]),
            run_id=str(row["run_id"]),
            status=RunStatus(str(row["status"])),
        )
