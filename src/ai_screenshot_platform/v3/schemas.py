from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


RunStatus = Literal["created", "running", "paused", "stopped", "completed", "failed"]
AppType = Literal["software", "pc_app", "pc_game", "game", "web", "auto"]
GameMode = Literal["menu", "gameplay", "auto"]
CaptureSource = Literal["obs", "folder_watch", "window"]
SafetyMode = Literal["strict", "review", "off"]
CaptureReason = Literal[
    "periodic",
    "before_action",
    "after_action",
    "rollback_after",
    "menu_state",
    "dialog_state",
]
CandidateRegionType = Literal["unknown", "content_area", "ui_chrome", "unsafe_chrome"]
UiStateHint = Literal[
    "editor",
    "main_view",
    "menu_file",
    "menu_edit",
    "menu_search",
    "menu_view",
    "menu_goto",
    "menu_zoom",
    "menu_favorites",
    "menu_settings",
    "menu_encoding",
    "menu_language",
    "menu_tools",
    "menu_macro",
    "menu_plugins",
    "menu_window",
    "menu_help",
    "dialog_about",
    "dialog_settings",
    "dialog_find",
    "dialog_replace",
    "dialog_preferences",
    "unknown",
]


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
    max_actions: int = Field(default=5, ge=1, le=20)
    safety_mode: SafetyMode = "strict"
    observe_only: bool = True
    must_have_text: bool = False
    game_mode: GameMode = "menu"
    allow_no_text_gameplay: bool = False
    max_game_actions: int = Field(default=5, ge=1, le=30)


class V3RunCreateRequest(BaseModel):
    config: V3TaskConfig = Field(default_factory=V3TaskConfig)


class V3ImageIngestRequest(BaseModel):
    image_path: str
    capture_reason: CaptureReason = "periodic"
    action_id: str | None = None
    ui_state_hint: UiStateHint = "unknown"


class V3ActionAuditRequest(BaseModel):
    action: dict[str, object]


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
    content_hash: str | None = None
    valid: bool = True
    near_duplicate: bool = False
    duplicate_decision: dict[str, object] = Field(default_factory=dict)
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
    candidate_region_type: CandidateRegionType = "unknown"
    candidate_source: str | None = None


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
    blocked_reason: str | None = None


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
    processed: int = 0
    accepted: int = 0
    rejected: int = 0
    failed: int = 0
    quarantined: int = 0
    manual_review_count: int = 0
    action_state_count: int = 0
    near_duplicate_count: int = 0
    exact_duplicate_count: int = 0
    action_representative_accepted_count: int = 0
    visual_difference_accepted_count: int = 0
    menu_state_accepted_count: int = 0
    dialog_state_accepted_count: int = 0
    periodic_static_rejected_count: int = 0
    duplicate_policy_summary: dict[str, object] = Field(default_factory=dict)
    duplicate_explanation_report_path: str | None = None
    frame_pump_restart_count: int = 0
    frame_pump_heartbeat: dict[str, object] = Field(default_factory=dict)
    content_area_blocked_count: int = 0
    ui_chrome_click_count: int = 0
    unsafe_chrome_blocked_count: int = 0
    reject_reason_distribution: dict[str, int] = Field(default_factory=dict)
    accepted_by_capture_reason: dict[str, int] = Field(default_factory=dict)
    accepted_by_ui_state_hint: dict[str, int] = Field(default_factory=dict)
    auto_click_count: int = 0
    menu_opened_count: int = 0
    dialog_opened_count: int = 0
    navigation_success_count: int = 0
    no_effect_count: int = 0
    blocked_count: int = 0
    rollback_count: int = 0
    risk_hit_count: int = 0
    observe_only: bool
    auto_click_ready: bool
    full_auto_capture_ready: bool = False
    model_ready: bool
    ocr_ready: bool
    ocr_gpu_ready: bool = False
    ocr_performance_ready: bool = False
    ocr_production_ready: bool = False
    input_gateway_ready: bool = False
    cursor_read_ready: bool = False
    mouse_click_ready: bool = False
    same_desktop_session_ready: bool = False
    same_integrity_ready: bool = False
    interactive_desktop_ready: bool = False
    click_backend: str = "dry_run_backend"
    input_gateway_blockers: list[str] = Field(default_factory=list)
    readiness_blockers: list[str] = Field(default_factory=list)
    safety_gate_ready: bool
    latest_event: V3Event | None = None


class ProviderHealth(BaseModel):
    provider: str
    status: Literal["ready", "degraded", "unavailable"]
    enabled: bool = False
    reason: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class InputGatewayHealth(BaseModel):
    input_gateway_ready: bool = False
    cursor_read_ready: bool = False
    mouse_click_ready: bool = False
    same_desktop_session_ready: bool = False
    same_integrity_ready: bool = False
    interactive_desktop_ready: bool = False
    click_backend: Literal["computer_use_backend", "win32_sendinput_backend", "pyautogui_backend", "dry_run_backend"] = "dry_run_backend"
    blockers: list[str] = Field(default_factory=list)
    diagnosis_path: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class V3Health(BaseModel):
    status: Literal["ready", "degraded"] = "degraded"
    ocr: list[ProviderHealth]
    models: list[ProviderHealth]
    complete_auto_mode_ready: bool
    full_auto_capture_ready: bool = False
    ocr_gpu_ready: bool = False
    ocr_performance_ready: bool = False
    ocr_production_ready: bool = False
    input_gateway_ready: bool = False
    cursor_read_ready: bool = False
    mouse_click_ready: bool = False
    same_desktop_session_ready: bool = False
    same_integrity_ready: bool = False
    interactive_desktop_ready: bool = False
    click_backend: str = "dry_run_backend"
    input_gateway_blockers: list[str] = Field(default_factory=list)
    input_gateway_diagnosis_path: str | None = None
    readiness_blockers: list[str] = Field(default_factory=list)
    ocr_performance: dict[str, object] = Field(default_factory=dict)
    frame_pump: dict[str, object] = Field(default_factory=dict)
    power_policy: dict[str, object] = Field(default_factory=dict)
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
