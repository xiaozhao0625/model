from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuntimeProfile:
    platform_type: str
    worker_type: str
    app_type: str = "unknown"
    recommended_bucket: str = "low"
    content_area_only: bool = False
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
