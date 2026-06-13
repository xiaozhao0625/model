from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QualityGatePolicy:
    min_width: int = 320
    min_height: int = 240
    near_duplicate_max_hamming_distance: int = 4
    ocr_enabled: bool = False

    @classmethod
    def from_json(cls, path: str | Path) -> QualityGatePolicy:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            min_width=int(data.get("min_width", 320)),
            min_height=int(data.get("min_height", 240)),
            near_duplicate_max_hamming_distance=int(data.get("near_duplicate_max_hamming_distance", 4)),
            ocr_enabled=bool(data.get("ocr_enabled", False)),
        )
