from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus


@dataclass(frozen=True)
class PcAppTargetConfig:
    app_id: str
    window_title: str
    process_name: str
    content_region: dict[str, int]
    bucket: Bucket = Bucket.LOW


@dataclass(frozen=True)
class PcAppCommand:
    command_id: str
    command_type: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PcAppCommandResult:
    command_id: str
    executed: bool
    skipped: bool
    reason: str


@dataclass(frozen=True)
class PcAppCapturedFrame:
    frame_id: str
    image_bytes: bytes
    bucket: Bucket
    source: str


class PcAppAutomationAdapter(Protocol):
    def focus_target(self, config: PcAppTargetConfig) -> PcAppCommandResult:
        ...

    def execute(self, command: PcAppCommand) -> PcAppCommandResult:
        ...

    def capture_frame(self, config: PcAppTargetConfig) -> PcAppCapturedFrame:
        ...


@dataclass(frozen=True)
class PcAppPipelineResult:
    status: RunStatus
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    run_dir: Path
    summary_path: Path
    captured_frame_count: int
    command_results: list[PcAppCommandResult]
    error: str | None = None
