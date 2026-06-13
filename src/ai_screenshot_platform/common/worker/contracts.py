from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus


class WorkerType(StrEnum):
    MOCK = "mock"
    PC_GAME = "pc_game"
    PC_APP = "pc_app"
    WEB = "web"
    ANDROID = "android"


class WorkerCapability(StrEnum):
    CAPTURE_LOW = "capture_low"
    CAPTURE_HIGH = "capture_high"
    MANUAL_GATE = "manual_gate"
    MODEL_GATEWAY = "model_gateway"
    BEHAVIOR_PACK = "behavior_pack"
    OBS_CAPTURE = "obs_capture"
    FFMPEG_EXTRACT = "ffmpeg_extract"
    ADB = "adb"
    PLAYWRIGHT = "playwright"
    PYWINAUTO = "pywinauto"
    UPLOAD_FLOW = "upload_flow"


class WorkerState(StrEnum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class WorkerProfile:
    worker_id: str
    machine_name: str
    worker_type: WorkerType
    gpu_name: str | None
    capabilities: set[WorkerCapability] = field(default_factory=set)
    state: WorkerState = WorkerState.IDLE
    current_run_id: str | None = None
    enabled: bool = True


@dataclass(frozen=True)
class WorkerTask:
    app_id: str
    run_id: str
    app_type: str
    platform: str
    target_min: int
    target_max: int
    bucket: str
    root_dir: str | Path


@dataclass(frozen=True)
class WorkerResult:
    app_id: str
    run_id: str
    status: RunStatus
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    run_dir: Path
    summary_path: Path
    error: str | None = None
