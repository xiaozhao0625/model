from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus


@dataclass(frozen=True)
class CaptureSourceConfig:
    source_name: str
    window_title: str
    fps: int
    width: int
    height: int


@dataclass(frozen=True)
class RecordingSession:
    session_id: str
    source_name: str
    started: bool
    output_path: Path


@dataclass(frozen=True)
class ExtractedFrame:
    frame_id: str
    timestamp_ms: int
    image_bytes: bytes
    bucket: Bucket


@dataclass(frozen=True)
class InputCommand:
    command_id: str
    command_type: str
    description: str
    duration_ms: int
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InputCommandResult:
    command_id: str
    executed: bool
    skipped: bool
    reason: str


class ObsCaptureAdapter(Protocol):
    def start_recording(self, config: CaptureSourceConfig) -> RecordingSession:
        ...

    def stop_recording(self, session: RecordingSession) -> RecordingSession:
        ...


class FfmpegExtractAdapter(Protocol):
    def extract_frames(
        self,
        session: RecordingSession,
        bucket: Bucket,
        max_frames: int,
    ) -> list[ExtractedFrame]:
        ...


class GameInputAdapter(Protocol):
    def execute(self, command: InputCommand) -> InputCommandResult:
        ...


@dataclass(frozen=True)
class PcGamePipelineResult:
    status: RunStatus
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    run_dir: Path
    summary_path: Path
    recording_session: RecordingSession
    input_results: list[InputCommandResult]
    extracted_frame_count: int
    error: str | None = None
