from __future__ import annotations

from pathlib import Path

from ai_screenshot_platform.workers.pc_game.contracts import (
    CaptureSourceConfig,
    RecordingSession,
)
from ai_screenshot_platform.workers.pc_game.health_check import check_pc_game_health
from ai_screenshot_platform.workers.runtime.health import ToolHealth


class RealObsCaptureAdapter:
    def __init__(self, enabled: bool = False, output_dir: str | Path = "runs/obs") -> None:
        self.enabled = enabled
        self.output_dir = Path(output_dir)

    def health(self) -> ToolHealth:
        if not self.enabled:
            return ToolHealth(
                name="obs",
                available=False,
                version=None,
                reason="disabled by config",
                required_for="pc game obs smoke",
            )
        return check_pc_game_health()["obs"]

    def start_recording(self, config: CaptureSourceConfig) -> RecordingSession:
        health = self.health()
        if not health.available:
            raise RuntimeError(f"obs unavailable: {health.reason}")
        import obsws_python

        self.output_dir.mkdir(parents=True, exist_ok=True)
        client = obsws_python.ReqClient()
        client.start_record()
        return RecordingSession(
            session_id=f"obs-recording-{config.source_name}",
            source_name=config.source_name,
            started=True,
            output_path=self.output_dir / f"{config.source_name}.mp4",
        )

    def stop_recording(self, session: RecordingSession) -> RecordingSession:
        health = self.health()
        if not health.available:
            raise RuntimeError(f"obs unavailable: {health.reason}")
        import obsws_python

        client = obsws_python.ReqClient()
        client.stop_record()
        return RecordingSession(
            session_id=session.session_id,
            source_name=session.source_name,
            started=False,
            output_path=session.output_path,
        )
