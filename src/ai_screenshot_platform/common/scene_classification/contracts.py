from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SceneClassificationResult:
    scene_class: str
    confidence: float
    reason: str
    hints_used: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
