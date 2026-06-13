from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus


@dataclass(frozen=True)
class AndroidTargetConfig:
    app_id: str
    package_name: str
    activity_name: str
    device_id: str
    bucket: Bucket = Bucket.LOW


@dataclass(frozen=True)
class AndroidDeviceCommand:
    command_id: str
    command_type: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AndroidDeviceCommandResult:
    command_id: str
    executed: bool
    skipped: bool
    reason: str


@dataclass(frozen=True)
class AndroidCapturedFrame:
    frame_id: str
    image_bytes: bytes
    bucket: Bucket
    source: str


@dataclass(frozen=True)
class AndroidUiObservation:
    app_id: str
    package_name: str
    activity_name: str
    source: str
    elements: list[dict[str, Any]]


@dataclass(frozen=True)
class AndroidQualityResult:
    valid: bool
    reason: str


class AndroidDeviceAdapter(Protocol):
    def connect(self, config: AndroidTargetConfig) -> AndroidDeviceCommandResult:
        ...

    def launch_app(self, config: AndroidTargetConfig) -> AndroidDeviceCommandResult:
        ...

    def execute(
        self,
        command: AndroidDeviceCommand,
    ) -> AndroidDeviceCommandResult:
        ...

    def capture_frame(self, config: AndroidTargetConfig) -> AndroidCapturedFrame:
        ...


class AndroidUiObserverAdapter(Protocol):
    def observe(self, config: AndroidTargetConfig) -> AndroidUiObservation:
        ...


class AndroidQualityAdapter(Protocol):
    def check(self, frame: AndroidCapturedFrame) -> AndroidQualityResult:
        ...


@dataclass(frozen=True)
class AndroidPipelineResult:
    status: RunStatus
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    run_dir: Path
    summary_path: Path
    captured_frame_count: int
    command_results: list[AndroidDeviceCommandResult]
    observation: AndroidUiObservation
    quality_results: list[AndroidQualityResult]
    error: str | None = None
