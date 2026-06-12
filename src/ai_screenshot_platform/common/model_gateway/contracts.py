from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class ModelTaskType(StrEnum):
    SCENE_CLASSIFY = "scene_classify"
    GROUND = "ground"
    ACT = "act"


class SceneClass(StrEnum):
    LAUNCHER = "launcher"
    LOGIN = "login"
    MENU = "menu"
    DOCUMENT = "document"
    BROWSER_PAGE = "browser_page"
    OPEN_WORLD = "open_world"
    COMBAT = "combat"
    SHOP = "shop"
    SCOREBOARD = "scoreboard"
    DEATH = "death"
    RESULT_SCREEN = "result_screen"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SceneClassifyRequest:
    app_id: str
    run_id: str
    screenshot_path: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SceneClassifyResult:
    scene_class: SceneClass
    confidence: float
    reason: str
    provider_name: str


@dataclass(frozen=True)
class GroundRequest:
    app_id: str
    run_id: str
    screenshot_path: str
    target_description: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GroundResult:
    found: bool
    x: int | None
    y: int | None
    confidence: float
    reason: str
    provider_name: str


class ActionType(StrEnum):
    CLICK = "click"
    KEY_PRESS = "key_press"
    WAIT = "wait"
    NO_OP = "no_op"
    REQUEST_MANUAL = "request_manual"
    ABORT = "abort"


@dataclass(frozen=True)
class ActionProposal:
    action_type: ActionType
    confidence: float
    reason: str
    target: dict[str, Any] | None = None
    keys: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    provider_name: str = ""


@dataclass(frozen=True)
class ActRequest:
    app_id: str
    run_id: str
    screenshot_path: str
    scene_class: SceneClass
    instruction: str
    context: dict[str, Any] = field(default_factory=dict)


class ModelGatewayProvider(Protocol):
    provider_name: str

    def scene_classify(
        self,
        request: SceneClassifyRequest,
    ) -> SceneClassifyResult:
        ...

    def ground(self, request: GroundRequest) -> GroundResult:
        ...

    def act(self, request: ActRequest) -> ActionProposal:
        ...
