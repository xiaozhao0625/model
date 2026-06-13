from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.workers.pc_game.contracts import (
    ExtractedFrame,
    RecordingSession,
)
from ai_screenshot_platform.workers.pc_game.health_check import check_pc_game_health
from ai_screenshot_platform.workers.runtime.health import ToolHealth


class RealFfmpegExtractAdapter:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def health(self) -> ToolHealth:
        if not self.enabled:
            return ToolHealth(
                name="ffmpeg",
                available=False,
                version=None,
                reason="disabled by config",
                required_for="pc game frame extraction smoke",
            )
        return check_pc_game_health()["ffmpeg"]

    def extract_frames(
        self,
        session: RecordingSession,
        bucket: Bucket,
        max_frames: int,
    ) -> list[ExtractedFrame]:
        health = self.health()
        if not health.available:
            raise RuntimeError(f"ffmpeg unavailable: {health.reason}")
        if not session.output_path.exists():
            raise RuntimeError(f"recording output does not exist: {session.output_path}")

        import subprocess

        with TemporaryDirectory() as temp_dir:
            pattern = str(Path(temp_dir) / "frame_%08d.png")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(session.output_path),
                    "-vframes",
                    str(max_frames),
                    pattern,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            frames = []
            for index, path in enumerate(sorted(Path(temp_dir).glob("frame_*.png"))):
                frames.append(
                    ExtractedFrame(
                        frame_id=f"{session.session_id}-real-frame-{index:08d}",
                        timestamp_ms=index * 100,
                        image_bytes=path.read_bytes(),
                        bucket=bucket,
                    )
                )
            return frames
