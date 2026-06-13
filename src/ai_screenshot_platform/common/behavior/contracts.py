from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus


class BehaviorPackError(ValueError):
    pass


class GameType(StrEnum):
    FPS = "fps"
    MOBA = "moba"
    OPEN_WORLD = "open_world"
    TWO_D_GAME = "2d_game"
    MOBILE_GAME = "mobile_game"


class BehaviorActionType(StrEnum):
    MOVE = "move"
    CAMERA = "camera"
    COMBAT = "combat"
    UI = "ui"
    RECOVERY = "recovery"
    WAIT = "wait"
    CAPTURE_HINT = "capture_hint"
    REQUEST_MANUAL = "request_manual"
    ABORT = "abort"


@dataclass(frozen=True)
class BehaviorAction:
    action_id: str
    action_type: BehaviorActionType
    description: str
    duration_ms: int
    bucket: Bucket | None
    risk_flags: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BehaviorPack:
    pack_id: str
    game_type: GameType
    version: str
    status: str
    allowed_context: list[str]
    forbidden_context: list[str]
    capture_bucket: Bucket
    record_then_extract: bool
    actions: list[BehaviorAction]


@dataclass(frozen=True)
class BehaviorSafetyDecision:
    action_type: BehaviorActionType
    blocked: bool
    reason: str
    risk_flags: list[str]


@dataclass(frozen=True)
class BehaviorRunResult:
    app_id: str
    run_id: str
    behavior_pack_id: str
    status: RunStatus
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    run_dir: Path
    actions_log_path: Path
    real_actions_executed: bool
    error: str | None = None
