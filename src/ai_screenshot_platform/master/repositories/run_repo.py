from __future__ import annotations

import sqlite3

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.models.entities import RunRecord


class RunRepo:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._columns = self._load_columns()
        self._has_worker_id = "worker_id" in self._columns

    def create(self, record: RunRecord) -> RunRecord:
        columns = [
            "run_id",
            "app_id",
            "status",
            "target_min",
            "target_max",
            "valid_total",
            "fixed_count",
            "low_count",
            "high_count",
            "rejected_count",
            "retry_round",
        ]
        values: list[object] = [
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
        ]
        if self._has_worker_id:
            columns.append("worker_id")
            values.append(record.worker_id)
        placeholders = ", ".join("?" for _ in columns)
        self.connection.execute(
            f"INSERT INTO runs ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )
        self.connection.commit()
        return record

    def list(self) -> list[RunRecord]:
        rows = self.connection.execute(
            f"""
            SELECT {self._select_columns()}
            FROM runs ORDER BY run_id
            """
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, run_id: str) -> RunRecord | None:
        row = self.connection.execute(
            f"""
            SELECT {self._select_columns()}
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
        if self._has_worker_id:
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
        else:
            self.connection.execute(
                """
            UPDATE runs
            SET status = ?,
                valid_total = ?,
                fixed_count = ?,
                low_count = ?,
                high_count = ?,
                rejected_count = ?
            WHERE run_id = ?
            """,
                (
                    status.value,
                    valid_total,
                    fixed_count,
                    low_count,
                    high_count,
                    rejected_count,
                    run_id,
                ),
            )
        self.connection.commit()
        record = self.get(run_id)
        if record is None:
            raise KeyError(f"run not found: {run_id}")
        return record

    def _load_columns(self) -> set[str]:
        try:
            rows = self.connection.execute("PRAGMA table_info(runs)").fetchall()
            return {str(row["name"]) for row in rows}
        except Exception:
            rollback = getattr(self.connection, "rollback", None)
            if rollback is not None:
                rollback()
            rows = self.connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'runs'
                """
            ).fetchall()
            return {str(row["column_name"]) for row in rows}

    def _select_columns(self) -> str:
        columns = [
            "run_id",
            "app_id",
            "status",
            "target_min",
            "target_max",
            "valid_total",
            "fixed_count",
            "low_count",
            "high_count",
            "rejected_count",
            "retry_round",
        ]
        if self._has_worker_id:
            columns.append("worker_id")
        return ", ".join(columns)

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
            worker_id=row["worker_id"] if self._has_worker_id else None,
        )
