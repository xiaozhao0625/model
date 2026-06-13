from __future__ import annotations

import json
import sqlite3

from ai_screenshot_platform.master.models.entities import WorkerRecord


class WorkerRepo:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert(self, record: WorkerRecord) -> WorkerRecord:
        self.connection.execute(
            """
            INSERT INTO workers (
                worker_id, type, machine_name, capabilities, state, heartbeat,
                current_run_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(worker_id) DO UPDATE SET
                type = excluded.type,
                machine_name = excluded.machine_name,
                capabilities = excluded.capabilities,
                state = excluded.state,
                heartbeat = excluded.heartbeat,
                current_run_id = excluded.current_run_id
            """,
            (
                record.worker_id,
                record.type,
                record.machine_name,
                json.dumps(record.capabilities),
                record.state,
                record.heartbeat,
                record.current_run_id,
            ),
        )
        self.connection.commit()
        return record

    def list(self) -> list[WorkerRecord]:
        rows = self.connection.execute(
            """
            SELECT worker_id, type, machine_name, capabilities, state, heartbeat,
                   current_run_id
            FROM workers ORDER BY worker_id
            """
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, worker_id: str) -> WorkerRecord | None:
        row = self.connection.execute(
            """
            SELECT worker_id, type, machine_name, capabilities, state, heartbeat,
                   current_run_id
            FROM workers WHERE worker_id = ?
            """,
            (worker_id,),
        ).fetchone()
        return self._from_row(row) if row is not None else None

    def _from_row(self, row: sqlite3.Row) -> WorkerRecord:
        return WorkerRecord(
            worker_id=str(row["worker_id"]),
            type=str(row["type"]),
            machine_name=str(row["machine_name"])
            if row["machine_name"] is not None
            else None,
            capabilities=list(json.loads(str(row["capabilities"]))),
            state=str(row["state"]),
            heartbeat=str(row["heartbeat"]) if row["heartbeat"] is not None else None,
            current_run_id=str(row["current_run_id"])
            if row["current_run_id"] is not None
            else None,
        )
