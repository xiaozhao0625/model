from __future__ import annotations

from dataclasses import dataclass, field

from ai_screenshot_platform.common.domain.run_status import RunStatus


@dataclass(frozen=True)
class AppRecord:
    app_id: str
    name: str
    type: str
    platform: str


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    app_id: str
    status: RunStatus
    target_min: int = 1000
    target_max: int = 5000
    valid_total: int = 0
    fixed_count: int = 0
    low_count: int = 0
    high_count: int = 0
    rejected_count: int = 0
    retry_round: int = 0
    worker_id: str | None = None


@dataclass(frozen=True)
class WorkerRecord:
    worker_id: str
    type: str
    machine_name: str | None = None
    capabilities: list[str] = field(default_factory=list)
    state: str = "idle"
    heartbeat: str | None = None
    current_run_id: str | None = None


@dataclass(frozen=True)
class ImageRecord:
    image_id: str
    run_id: str
    bucket: str
    path: str
    hash: str


@dataclass(frozen=True)
class UploadRecord:
    upload_id: str
    run_id: str
    status: RunStatus
