from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.domain.run_status import RunStatus


class RunEventLogger:
    def __init__(self, run_dir: str | Path, app_id: str, run_id: str) -> None:
        self.run_dir = Path(run_dir)
        self.app_id = app_id
        self.run_id = run_id
        self.log_path = self.run_dir / "run.log"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event: str,
        status: RunStatus,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "app_id": self.app_id,
            "run_id": self.run_id,
            "event": event,
            "status": status.value,
            "details": details or {},
        }
        with self.log_path.open("a", encoding="utf-8", newline="\n") as log_file:
            log_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            log_file.write("\n")
        return record
