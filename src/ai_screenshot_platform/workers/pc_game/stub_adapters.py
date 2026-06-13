from __future__ import annotations

from pathlib import Path

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.workers.pc_game.contracts import (
    CaptureSourceConfig,
    ExtractedFrame,
    InputCommand,
    InputCommandResult,
    RecordingSession,
)


class StubObsCaptureAdapter:
    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def start_recording(self, config: CaptureSourceConfig) -> RecordingSession:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return RecordingSession(
            session_id=f"stub-recording-{config.source_name}",
            source_name=config.source_name,
            started=True,
            output_path=self.output_dir / f"{config.source_name}.stub.mp4",
        )

    def stop_recording(self, session: RecordingSession) -> RecordingSession:
        return RecordingSession(
            session_id=session.session_id,
            source_name=session.source_name,
            started=False,
            output_path=session.output_path,
        )


class StubFfmpegExtractAdapter:
    def extract_frames(
        self,
        session: RecordingSession,
        bucket: Bucket,
        max_frames: int,
    ) -> list[ExtractedFrame]:
        return [
            ExtractedFrame(
                frame_id=f"{session.session_id}-frame-{index:08d}",
                timestamp_ms=index * 100,
                image_bytes=(
                    f"{session.session_id}:{bucket.value}:frame:{index}"
                ).encode("utf-8"),
                bucket=bucket,
            )
            for index in range(max_frames)
        ]


class StubGameInputAdapter:
    def execute(self, command: InputCommand) -> InputCommandResult:
        return InputCommandResult(
            command_id=command.command_id,
            executed=False,
            skipped=True,
            reason="stub adapter skipped real input execution",
        )
