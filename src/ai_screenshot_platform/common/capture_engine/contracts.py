from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CaptureDecisionInput:
    app_type: str = "unknown"
    scene_class: str = "unknown"
    quality_accepted: bool = True
    reject_reason: str | None = None
    profile_bucket: str = "low"
    fixed_candidate: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaptureBucketDecision:
    bucket: str
    valid: bool
    reject_reason: str | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
