from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


RunStatus = Literal["created", "running", "paused", "stopped", "completed", "failed"]
AppType = Literal["software", "game", "auto"]
CaptureSource = Literal["obs", "folder_watch", "window"]
SafetyMode = Literal["strict", "review", "off"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class V3TaskConfig(BaseModel):
    app_name: str = "manual_target"
    app_type: AppType = "auto"
    target_language: str = "zh"
    capture_source: CaptureSource = "folder_watch"
    capture_interval_ms: int = Field(default=1000, ge=100, le=60000)
    save_root: str = "runs/v3"
    enable_ocr: bool = True
    enable_ui_model: bool = True
    enable_auto_click: bool = False
    enable_game_explorer: bool = False
    delete_rejected: bool = False
    max_images: int = Field(default=100, ge=1, le=50000)
    safety_mode: SafetyMode = "strict"
    observe_only: bool = True
    must_have_text: bool = False


class V3RunCreateRequest(BaseModel):
    config: V3TaskConfig = Field(default_factory=V3TaskConfig)


class V3RunRecord(BaseModel):
    run_id: str
    status: RunStatus = "created"
    config: V3TaskConfig
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    counts: dict[str, int] = Field(
        default_factory=lambda: {
            "pending": 0,
            "accepted": 0,
            "rejected": 0,
            "deleted": 0,
            "manual_review": 0,
            "events": 0,
            "actions": 0,
        }
    )
    last_error: str | None = None


class V3ImageRecord(BaseModel):
    image_id: str
    path: str
    bucket: Literal["pending", "accepted", "rejected", "deleted", "manual_review"] = "pending"
    sha256: str | None = None
    reject_reason: str | None = None
    created_at: str = Field(default_factory=utc_now)
    meta: dict[str, object] = Field(default_factory=dict)


class OcrTextBox(BaseModel):
    text: str
    bbox: list[int]
    confidence: float = 0.0
    language_hint: str | None = None


class OcrResult(BaseModel):
    provider: str
    status: Literal["ok", "unavailable", "error"]
    text_boxes: list[OcrTextBox] = Field(default_factory=list)
    error: str | None = None


class ModelClickCandidate(BaseModel):
    label: str
    source: str
    bbox: list[int]
    click_x: int
    click_y: int
    confidence: float
    reason: str
    risk_flags: list[str] = Field(default_factory=list)


class SceneClassification(BaseModel):
    scene_class: Literal[
        "software_ui",
        "game_menu",
        "game_loading",
        "game_in_match",
        "game_unknown",
        "unsafe_page",
    ] = "software_ui"
    confidence: float = 0.0
    reason: str = "not_evaluated"


class ModelResult(BaseModel):
    provider: str
    status: Literal["ok", "unavailable", "degraded", "error"]
    scene: SceneClassification = Field(default_factory=SceneClassification)
    candidates: list[ModelClickCandidate] = Field(default_factory=list)
    raw_response_path: str | None = None
    error: str | None = None


class FusedCandidate(ModelClickCandidate):
    final_score: float
    ocr_button_score: float = 0.0
    ui_model_score: float = 0.0
    layout_score: float = 0.0
    history_score: float = 0.0
    risk_penalty: float = 0.0
    blocked: bool = False
    block_reason: str | None = None


class ActionDecision(BaseModel):
    action: Literal["click", "esc", "alt_left", "backspace", "wait", "wasd", "mouse_move_small", "space", "shift_short", "e_or_f_interact_low_frequency"]
    allowed: bool
    reason: str
    candidate: FusedCandidate | None = None


class V3Event(BaseModel):
    timestamp: str = Field(default_factory=utc_now)
    event: str
    details: dict[str, object] = Field(default_factory=dict)


class V3Summary(BaseModel):
    run_id: str
    status: RunStatus
    counts: dict[str, int]
    observe_only: bool
    auto_click_ready: bool
    model_ready: bool
    ocr_ready: bool
    safety_gate_ready: bool
    latest_event: V3Event | None = None


class ProviderHealth(BaseModel):
    provider: str
    status: Literal["ready", "degraded", "unavailable"]
    enabled: bool = False
    reason: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class V3Health(BaseModel):
    status: Literal["ready", "degraded"] = "degraded"
    ocr: list[ProviderHealth]
    models: list[ProviderHealth]
    complete_auto_mode_ready: bool
    defaults: V3TaskConfig


class ModelRequest(BaseModel):
    screenshot_path: str
    task_context: dict[str, object] = Field(default_factory=dict)
    ocr_boxes: list[OcrTextBox] = Field(default_factory=list)


def ensure_run_dir(save_root: str, run_id: str) -> Path:
    root = Path(save_root).resolve()
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
