from __future__ import annotations

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.runtime.run_session import LocalRunSession
from ai_screenshot_platform.workers.pc_game.contracts import (
    CaptureSourceConfig,
    FfmpegExtractAdapter,
    GameInputAdapter,
    InputCommand,
    ObsCaptureAdapter,
    PcGamePipelineResult,
)


class PcGameStubPipeline:
    def __init__(
        self,
        session: LocalRunSession,
        obs_adapter: ObsCaptureAdapter,
        ffmpeg_adapter: FfmpegExtractAdapter,
        input_adapter: GameInputAdapter,
    ) -> None:
        self.session = session
        self.obs_adapter = obs_adapter
        self.ffmpeg_adapter = ffmpeg_adapter
        self.input_adapter = input_adapter

    def run(
        self,
        config: CaptureSourceConfig,
        max_frames: int,
    ) -> PcGamePipelineResult:
        recording = self.obs_adapter.start_recording(config)
        input_results = [
            self.input_adapter.execute(command)
            for command in self._mock_input_commands()
        ]
        stopped_recording = self.obs_adapter.stop_recording(recording)

        self.session.start()
        frames = self.ffmpeg_adapter.extract_frames(
            stopped_recording,
            bucket=Bucket.HIGH,
            max_frames=max_frames,
        )
        for frame in frames:
            self.session.save_image(frame.bucket, frame.image_bytes)
        self.session.evaluate_completion()
        summary = self.session.generate_summary()

        return PcGamePipelineResult(
            status=self.session.status,
            valid_total=int(summary["valid_total"]),
            fixed_count=int(summary["fixed_count"]),
            low_count=int(summary["low_count"]),
            high_count=int(summary["high_count"]),
            rejected_count=int(summary["rejected_count"]),
            run_dir=self.session.run_dir,
            summary_path=self.session.run_dir / "summary.json",
            recording_session=stopped_recording,
            input_results=input_results,
            extracted_frame_count=len(frames),
        )

    def _mock_input_commands(self) -> list[InputCommand]:
        return [
            InputCommand(
                command_id="stub_move",
                command_type="move",
                description="Stub movement command; no real input is executed.",
                duration_ms=100,
                params={"pattern": "forward"},
            ),
            InputCommand(
                command_id="stub_camera",
                command_type="camera",
                description="Stub camera command; no real input is executed.",
                duration_ms=100,
                params={"yaw_delta": 15},
            ),
        ]
