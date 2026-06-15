from __future__ import annotations

import re
from datetime import datetime

from ai_screenshot_platform.common.domain.run_lifecycle import RunLifecycle
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.models.entities import RunRecord
from ai_screenshot_platform.master.models.entities import RunStatusEvent
from ai_screenshot_platform.master.repositories.run_repo import RunRepo


class RunService:
    def __init__(
        self,
        run_repo: RunRepo,
        lifecycle: RunLifecycle | None = None,
    ) -> None:
        self.run_repo = run_repo
        self.lifecycle = lifecycle or RunLifecycle()

    def create_run(
        self,
        run_id: str,
        app_id: str,
        target_min: int = 1000,
        target_max: int = 5000,
    ) -> RunRecord:
        return self.run_repo.create(
            RunRecord(
                run_id=run_id,
                app_id=app_id,
                status=RunStatus.PENDING,
                target_min=target_min,
                target_max=target_max,
            )
        )

    def list(self) -> list[RunRecord]:
        return self.run_repo.list()

    def list_api(self) -> list[dict[str, int | str | None]]:
        return [self.to_api_record(record) for record in self.list()]

    def query_api(
        self,
        status: str | None = None,
        worker_id: str | None = None,
        app_id: str | None = None,
        batch: str | None = None,
        q: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
        sort: str = "created_at_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        records = [self.to_api_record(record) for record in self.list()]
        filters = {
            "status": status or None,
            "worker_id": worker_id or None,
            "app_id": app_id or None,
            "batch": batch or None,
            "q": q or None,
            "created_from": created_from or None,
            "created_to": created_to or None,
        }

        filtered = [
            record
            for record in records
            if self._matches_query(record, filters)
        ]
        filtered = [
            record
            for record in filtered
            if self._matches_created_window(record, created_from, created_to)
        ]
        sorted_records = self._sort_records(filtered, sort)
        bounded_limit = max(1, min(int(limit), 200))
        bounded_offset = max(0, int(offset))
        items = sorted_records[bounded_offset : bounded_offset + bounded_limit]
        return {
            "items": items,
            "total": len(sorted_records),
            "limit": bounded_limit,
            "offset": bounded_offset,
            "sort": sort,
            "filters": filters,
        }

    def get(self, run_id: str) -> RunRecord:
        record = self.run_repo.get(run_id)
        if record is None:
            raise KeyError(f"run not found: {run_id}")
        return record

    def get_api(self, run_id: str) -> dict[str, int | str | None]:
        return self.to_api_record(self.get(run_id))

    def start_run(self, run_id: str) -> RunRecord:
        record = self.get(run_id)
        status = self.lifecycle.transition(record.status, RunStatus.LAUNCHING)
        status = self.lifecycle.transition(status, RunStatus.PROFILING)
        status = self.lifecycle.transition(status, RunStatus.RUNNING)
        return self.run_repo.update_status(run_id, status)

    def mark_failed_low_yield(
        self,
        run_id: str,
        operator_action: str = "mark_failed_low_yield",
    ) -> dict[str, int | str | None]:
        record = self.get(run_id)
        if record.status == RunStatus.SKIPPED_RISK:
            raise ValueError("skipped risk runs cannot be marked failed low yield")
        if record.status != RunStatus.FAILED_LOW_YIELD:
            self.run_repo.update_status(run_id, RunStatus.FAILED_LOW_YIELD)
            self.run_repo.record_status_event(
                run_id=run_id,
                previous_status=record.status,
                new_status=RunStatus.FAILED_LOW_YIELD,
                operator_action=operator_action,
            )
        return self.get_api(run_id)

    def status_events(self, run_id: str) -> list[RunStatusEvent]:
        self.get(run_id)
        return self.run_repo.status_events(run_id)

    def summary(self, run_id: str) -> dict[str, int | str | None]:
        record = self.get(run_id)
        return {
            "run_id": record.run_id,
            "app_id": record.app_id,
            "status": record.status.value,
            "target_min": record.target_min,
            "target_max": record.target_max,
            "valid_total": record.valid_total,
            "fixed_count": record.fixed_count,
            "low_count": record.low_count,
            "high_count": record.high_count,
            "rejected_count": record.rejected_count,
            "retry_round": record.retry_round,
            "worker_id": self.worker_id_for(record),
            "assigned_worker_id": self.worker_id_for(record),
            "executed_by": self.worker_id_for(record),
        }

    def to_api_record(self, record: RunRecord) -> dict[str, int | str | None]:
        worker_id = self.worker_id_for(record)
        created_at = derived_run_created_at(record.run_id)
        return {
            "run_id": record.run_id,
            "app_id": record.app_id,
            "status": record.status.value,
            "target_min": record.target_min,
            "target_max": record.target_max,
            "valid_total": record.valid_total,
            "fixed_count": record.fixed_count,
            "low_count": record.low_count,
            "high_count": record.high_count,
            "rejected_count": record.rejected_count,
            "retry_round": record.retry_round,
            "worker_id": worker_id,
            "assigned_worker_id": worker_id,
            "executed_by": worker_id,
            "created_at": created_at,
            "updated_at": created_at,
            "batch": infer_batch_from_run_id(record.run_id),
        }

    def worker_id_for(self, record: RunRecord) -> str | None:
        if record.worker_id:
            return record.worker_id
        return infer_worker_id_from_run_id(record.run_id)

    def _matches_query(self, record: dict[str, int | str | None], filters: dict[str, str | None]) -> bool:
        status = filters["status"]
        if status and status != "all" and record.get("status") != status:
            return False
        worker_id = filters["worker_id"]
        if worker_id and worker_id != "all":
            actual_worker = record.get("worker_id")
            if worker_id == "unassigned":
                if actual_worker:
                    return False
            elif actual_worker != worker_id:
                return False
        app_id = filters["app_id"]
        if app_id and app_id != "all" and record.get("app_id") != app_id:
            return False
        batch = filters["batch"]
        if batch and batch not in {"all", "latest"} and record.get("batch") != batch:
            return False
        query = (filters["q"] or "").strip().lower()
        if query:
            haystack = " ".join(
                str(record.get(key) or "")
                for key in ("run_id", "app_id", "worker_id", "assigned_worker_id", "executed_by")
            ).lower()
            if query not in haystack:
                return False
        return True

    def _matches_created_window(
        self,
        record: dict[str, int | str | None],
        created_from: str | None,
        created_to: str | None,
    ) -> bool:
        created = parse_api_datetime(str(record.get("created_at") or ""))
        if created is None:
            return True
        start = parse_api_datetime(created_from or "")
        end = parse_api_datetime(created_to or "")
        if start and created < start:
            return False
        if end and created > end:
            return False
        return True

    def _sort_records(self, records: list[dict[str, int | str | None]], sort: str) -> list[dict[str, int | str | None]]:
        if sort == "created_at_asc":
            return sorted(records, key=sort_time_key)
        if sort == "updated_at_desc":
            return sorted(records, key=sort_time_key, reverse=True)
        if sort == "valid_total_desc":
            return sorted(records, key=lambda item: int(item.get("valid_total") or 0), reverse=True)
        if sort == "status_priority":
            priority = {
                "failed_low_yield": 0,
                "skipped_risk": 1,
                "waiting_manual": 2,
                "running": 3,
                "launching": 4,
                "pending": 5,
                "capture_completed": 6,
                "completed": 7,
            }
            return sorted(records, key=lambda item: (priority.get(str(item.get("status")), 99), sort_time_key(item)), reverse=False)
        if sort == "worker_id_asc":
            return sorted(records, key=lambda item: (str(item.get("worker_id") or "zzzz"), sort_time_key(item)))
        return sorted(records, key=sort_time_key, reverse=True)


def infer_worker_id_from_run_id(run_id: str) -> str | None:
    normalized = run_id.lower()
    if "_w1_" in normalized or normalized.startswith("p14_w1_") or "safe_window" in normalized:
        return "worker_pc_game_w1"
    if "_w2_" in normalized or normalized.startswith("p14_w2_") or "web_content" in normalized:
        return "worker_pc_app_web_w2"
    if "_w3_" in normalized or normalized.startswith("p14_w3_") or "android" in normalized:
        return "worker_android_w3"
    return None


def infer_batch_from_run_id(run_id: str) -> str | None:
    normalized = run_id.lower()
    if "p14_4_batch3" in normalized:
        return "p14_4_batch3"
    if "p14_4_batch2" in normalized:
        return "p14_4_batch2"
    if "p14_4_batch1" in normalized:
        return "p14_4_batch1"
    if "p14_3" in normalized:
        return "p14_3"
    return None


def derived_run_created_at(run_id: str) -> str | None:
    match = re.search(r"(20\d{6})_(\d{6})", run_id)
    if not match:
        return None
    try:
        parsed = datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return parsed.isoformat()


def parse_api_datetime(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return datetime.strptime(value, "%Y-%m-%d")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def sort_time_key(record: dict[str, int | str | None]) -> tuple[str, str]:
    return (str(record.get("created_at") or ""), str(record.get("run_id") or ""))
