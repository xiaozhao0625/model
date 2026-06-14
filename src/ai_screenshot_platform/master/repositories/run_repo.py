from __future__ import annotations

import sqlite3

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.models.entities import RunRecord


class RunRepo:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, record: RunRecord) -> RunRecord:
        self.connection.execute(
            """
            INSERT INTO runs (
                run_id, app_id, status, target_min, target_max, valid_total,
                fixed_count, low_count,
                high_count, rejected_count, retry_round, worker_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.run_id,
                record.app_id,
                record.status.value,
                record.target_min,
                record.target_max,
                record.valid_total,
                record.fixed_count,
                record.low_count,
                record.high_count,
                record.rejected_count,
                record.retry_round,
                record.worker_id,
            ),
        )
        self.connection.commit()
        return record

    def list(self) -> list[RunRecord]:
        rows = self.connection.execute(
            """
            SELECT run_id, app_id, status, target_min, target_max, valid_total, fixed_count, low_count,
                   high_count, rejected_count, retry_round, worker_id
            FROM runs ORDER BY run_id
            """
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, run_id: str) -> RunRecord | None:
        row = self.connection.execute(
            """
            SELECT run_id, app_id, status, target_min, target_max, valid_total, fixed_count, low_count,
                   high_count, rejected_count, retry_round, worker_id
            FROM runs WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        return self._from_row(row) if row is not None else None

    def update_status(self, run_id: str, status: RunStatus) -> RunRecord:
        self.connection.execute(
            "UPDATE runs SET status = ? WHERE run_id = ?",
            (status.value, run_id),
        )
        self.connection.commit()
        record = self.get(run_id)
        if record is None:
            raise KeyError(f"run not found: {run_id}")
        return record

    def update_from_worker_result(
        self,
        run_id: str,
        status: RunStatus,
        valid_total: int,
        fixed_count: int,
        low_count: int,
        high_count: int,
        rejected_count: int,
        worker_id: str | None = None,
    ) -> RunRecord:
        self.connection.execute(
            """
            UPDATE runs
            SET status = ?,
                valid_total = ?,
                fixed_count = ?,
                low_count = ?,
                high_count = ?,
                rejected_count = ?,
                worker_id = ?
            WHERE run_id = ?
            """,
            (
                status.value,
                valid_total,
                fixed_count,
                low_count,
                high_count,
                rejected_count,
                worker_id,
                run_id,
            ),
        )
        self.connection.commit()
        record = self.get(run_id)
        if record is None:
            raise KeyError(f"run not found: {run_id}")
        return record

    def _from_row(self, row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=str(row["run_id"]),
            app_id=str(row["app_id"]),
            status=RunStatus(str(row["status"])),
            target_min=int(row["target_min"]),
            target_max=int(row["target_max"]),
            valid_total=int(row["valid_total"]),
            fixed_count=int(row["fixed_count"]),
            low_count=int(row["low_count"]),
            high_count=int(row["high_count"]),
            rejected_count=int(row["rejected_count"]),
            retry_round=int(row["retry_round"]),
            worker_id=row["worker_id"],
        )
