from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CaptureEnginePolicy:
    default_bucket: str = "low"
    game_bucket: str = "high"
    reject_risky_scenes: bool = True

    @classmethod
    def from_json(cls, path: str | Path) -> CaptureEnginePolicy:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            default_bucket=str(data.get("default_bucket", "low")),
            game_bucket=str(data.get("game_bucket", "high")),
            reject_risky_scenes=bool(data.get("reject_risky_scenes", True)),
        )
