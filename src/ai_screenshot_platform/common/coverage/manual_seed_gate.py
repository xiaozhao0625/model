from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_screenshot_platform.common.domain.run_lifecycle import (
    RunLifecycle,
    RunTransitionError,
)
from ai_screenshot_platform.common.domain.run_status import RunStatus


class ManualSeedError(ValueError):
    pass


@dataclass(frozen=True)
class ManualSeedRecord:
    app_id: str
    run_id: str
    event: str
    status: str
    reason: str
    retry_round: int
    operator: str
    note: str
    timestamp: str


class ManualSeedGate:
    def __init__(
        self,
        run_dir: str | Path,
        app_id: str,
        run_id: str,
        lifecycle: RunLifecycle | None = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.app_id = app_id
        self.run_id = run_id
        self.lifecycle = lifecycle or RunLifecycle()
        self.record_path = self.run_dir / "manual_seed_record.jsonl"

    def request_manual_seed(
        self,
        current_status: RunStatus,
        reason: str,
        retry_round: int,
        operator: str,
        note: str = "",
    ) -> ManualSeedRecord:
        next_status = self._transition(
            current_status,
            RunStatus.NEEDS_MANUAL_SEED,
        )
        return self._write_record(
            event="manual_seed_requested",
            status=next_status,
            reason=reason,
            retry_round=retry_round,
            operator=operator,
            note=note,
        )

    def resume_after_manual_seed(
        self,
        current_status: RunStatus,
        reason: str,
        retry_round: int,
        operator: str,
        note: str = "",
    ) -> ManualSeedRecord:
        next_status = self._transition(current_status, RunStatus.RUNNING)
        return self._write_record(
            event="manual_seed_completed",
            status=next_status,
            reason=reason,
            retry_round=retry_round,
            operator=operator,
            note=note,
        )

    def _transition(
        self,
        current_status: RunStatus,
        next_status: RunStatus,
    ) -> RunStatus:
        try:
            return self.lifecycle.transition(current_status, next_status)
        except RunTransitionError as error:
            raise ManualSeedError(str(error)) from error

    def _write_record(
        self,
        event: str,
        status: RunStatus,
        reason: str,
        retry_round: int,
        operator: str,
        note: str,
    ) -> ManualSeedRecord:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        record = ManualSeedRecord(
            app_id=self.app_id,
            run_id=self.run_id,
            event=event,
            status=status.value,
            reason=reason,
            retry_round=retry_round,
            operator=operator,
            note=note,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        with self.record_path.open("a", encoding="utf-8", newline="\n") as record_file:
            record_file.write(
                json.dumps(asdict(record), ensure_ascii=False, sort_keys=True)
            )
            record_file.write("\n")
        return record
