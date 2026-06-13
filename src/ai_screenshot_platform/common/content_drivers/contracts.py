from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentDriverStep:
    action_type: str
    description: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ContentDriverPlan:
    driver_type: str
    steps: list[ContentDriverStep]
    safe: bool = True
