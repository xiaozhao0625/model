from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from ai_screenshot_platform.common.domain.completion_gate import (
    CaptureCounts,
    CompletionGate,
)
from ai_screenshot_platform.common.domain.run_status import RunStatus


class RunStatusResolveError(ValueError):
    pass


class RunStatusResolver:
    def __init__(self, completion_gate: CompletionGate | None = None) -> None:
        self.completion_gate = completion_gate or CompletionGate()

    def resolve(self, run_dir: str | Path) -> RunStatus:
        resolved_run_dir = Path(run_dir).resolve()

        if self._has_completed_event(resolved_run_dir / "run.log"):
            return RunStatus.COMPLETED
        if (resolved_run_dir / "cleanup_record.json").is_file():
            return RunStatus.LOCAL_DELETED
        if (resolved_run_dir / "upload_record.json").is_file():
            return RunStatus.UPLOADED_CONFIRMED
        if (resolved_run_dir / "upload_manifest.json").is_file():
            return RunStatus.UPLOAD_PENDING
        if self._summary_is_capture_completed(resolved_run_dir / "summary.json"):
            return RunStatus.CAPTURE_COMPLETED
        return RunStatus.RUNNING

    def _has_completed_event(self, run_log_path: Path) -> bool:
        if not run_log_path.is_file():
            return False

        for line_number, line in enumerate(
            run_log_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except JSONDecodeError as exc:
                raise RunStatusResolveError(
                    f"invalid JSON in run.log at line {line_number}"
                ) from exc
            if not isinstance(event, dict):
                raise RunStatusResolveError(
                    f"invalid run.log event at line {line_number}"
                )
            if event.get("event") == RunStatus.COMPLETED.value:
                return True
        return False

    def _summary_is_capture_completed(self, summary_path: Path) -> bool:
        if not summary_path.is_file():
            return False

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        counts = CaptureCounts(
            fixed=int(summary.get("fixed_count", 0)),
            low=int(summary.get("low_count", 0)),
            high=int(summary.get("high_count", 0)),
            rejected=int(summary.get("rejected_count", 0)),
        )
        return (
            self.completion_gate.evaluate(counts).next_status
            == RunStatus.CAPTURE_COMPLETED
        )
