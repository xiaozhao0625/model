from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus


@dataclass(frozen=True)
class WebTargetConfig:
    app_id: str
    url: str
    viewport_width: int
    viewport_height: int
    content_area_only: bool = True
    bucket: Bucket = Bucket.LOW


@dataclass(frozen=True)
class WebCommand:
    command_id: str
    command_type: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebCommandResult:
    command_id: str
    executed: bool
    skipped: bool
    reason: str


@dataclass(frozen=True)
class WebCapturedFrame:
    frame_id: str
    image_bytes: bytes
    bucket: Bucket
    source: str
    content_area_only: bool


class WebAutomationAdapter(Protocol):
    def open_target(self, config: WebTargetConfig) -> WebCommandResult:
        ...

    def execute(self, command: WebCommand) -> WebCommandResult:
        ...

    def capture_frame(self, config: WebTargetConfig) -> WebCapturedFrame:
        ...


@dataclass(frozen=True)
class WebPipelineResult:
    status: RunStatus
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    run_dir: Path
    summary_path: Path
    captured_frame_count: int
    command_results: list[WebCommandResult]
    content_area_only: bool
    error: str | None = None
