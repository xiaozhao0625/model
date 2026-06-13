from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any


class BehaviorLearningOutputStore:
    forbidden_output_parts = {"fixed", "low", "high", "rejected", "temp_video"}

    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)

    def run_output_dir(self, app_id: str, run_id: str) -> Path:
        output_dir = self.output_root / app_id / run_id
        if set(output_dir.parts) & self.forbidden_output_parts:
            raise ValueError("behavior learning output must not be inside capture buckets")
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def write_json(self, path: Path, payload: Any) -> Path:
        if hasattr(payload, "to_dict"):
            data = payload.to_dict()
        elif hasattr(payload, "__dataclass_fields__"):
            data = asdict(payload)
        else:
            data = payload
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path
