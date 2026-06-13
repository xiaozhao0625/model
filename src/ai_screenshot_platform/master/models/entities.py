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
    valid_total: int = 0
    fixed_count: int = 0
    low_count: int = 0
    high_count: int = 0
    rejected_count: int = 0
    retry_round: int = 0


@dataclass(frozen=True)
class WorkerRecord:
    worker_id: str
    type: str
    capabilities: list[str] = field(default_factory=list)
    state: str = "idle"
    heartbeat: str | None = None


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
