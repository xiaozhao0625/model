from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AppCreateRequest(BaseModel):
    app_id: str
    name: str
    type: str
    platform: str


class RunCreateRequest(BaseModel):
    run_id: str
    app_id: str
    target_min: int = 1000
    target_max: int = 5000


class WorkerRegisterRequest(BaseModel):
    worker_id: str
    type: str
    machine_name: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class WorkerResultReportRequest(BaseModel):
    app_id: str
    run_id: str
    status: str
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    run_dir: str
    summary_path: str
    error: str | None = None
    behavior_pack_id: str | None = None
    behavior_actions_path: str | None = None


class UploadRunRequest(BaseModel):
    run_id: str


class RunManualStatusRequest(BaseModel):
    operator_action: str = "mark_failed_low_yield"


class SceneClassifyApiRequest(BaseModel):
    app_id: str
    run_id: str
    screenshot_path: str
    context: dict[str, Any] = Field(default_factory=dict)


class GroundApiRequest(BaseModel):
    app_id: str
    run_id: str
    screenshot_path: str
    target_description: str
    context: dict[str, Any] = Field(default_factory=dict)


class ActApiRequest(BaseModel):
    app_id: str
    run_id: str
    screenshot_path: str
    scene_class: str
    instruction: str
    target_description: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class QualityReportIngestRequest(BaseModel):
    app_id: str = ""
    run_id: str
    total_images: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    quality_pass_rate: float = 0
    black_screen_count: int = 0
    white_screen_count: int = 0
    blurry_count: int = 0
    wrong_window_count: int = 0
    browser_chrome_count: int = 0
    taskbar_count: int = 0
    near_duplicate_count: int = 0
    ocr_risk_hit_count: int = 0
    reject_reason_distribution: dict[str, int] = Field(default_factory=dict)
    bucket_distribution: dict[str, int] = Field(default_factory=dict)
    source_path: str | None = None


class OcrReportIngestRequest(BaseModel):
    app_id: str = ""
    run_id: str
    provider: str = "disabled"
    available: bool = False
    status: str = "unknown"
    risk_hits: list[str] = Field(default_factory=list)
    scene_hints: list[str] = Field(default_factory=list)
    unavailable_reason: str | None = None
    paddleocr_optional_status: str = "unknown"
    easyocr_optional_status: str = "unknown"
    source_path: str | None = None


class AndroidToolHealthPayload(BaseModel):
    profile_id: str | None = None
    adb_available: bool = False
    devices: list[str] = Field(default_factory=list)
    selected_device: str | None = None
    screencap_status: str = "unknown"
    ui_dump_status: str = "unknown"
    ocr_fallback_status: str = "unknown"
    input_status: str = "unknown"
    skipped_reason: str | None = None


class ToolHealthIngestRequest(BaseModel):
    machine_name: str | None = None
    worker_id: str | None = None
    worker_type: str | None = None
    status: str = "unknown"
    tools: dict[str, str] = Field(default_factory=dict)
    master_ready: dict[str, Any] = Field(default_factory=dict)
    worker_ready: dict[str, Any] = Field(default_factory=dict)
    android: AndroidToolHealthPayload | None = None
    source_path: str | None = None


class BehaviorCandidateIngestRequest(BaseModel):
    candidate_pack_id: str
    base_pack_id: str = ""
    game_type: str = ""
    version: str = ""
    status: str = "pending_review"
    enabled: bool = False
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    rollback_target: str = ""
    created_from_run_id: str = ""
    pack_content: dict[str, Any] = Field(default_factory=dict)
    source_path: str | None = None


class BehaviorCandidateReviewRequest(BaseModel):
    reviewer: str | None = None
    reason: str | None = None


class DiagnosticIngestRequest(BaseModel):
    machine_name: str | None = None
    role: str | None = None
    status: str = "unknown"
    report_type: str = "diagnostic"
    payload: dict[str, Any] = Field(default_factory=dict)
    source_path: str | None = None
