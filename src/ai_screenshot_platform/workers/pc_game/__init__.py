from ai_screenshot_platform.workers.pc_game.contracts import (
    CaptureSourceConfig,
    ExtractedFrame,
    FfmpegExtractAdapter,
    GameInputAdapter,
    InputCommand,
    InputCommandResult,
    ObsCaptureAdapter,
    PcGamePipelineResult,
    RecordingSession,
)
from ai_screenshot_platform.workers.pc_game.pipeline import PcGameStubPipeline
from ai_screenshot_platform.workers.pc_game.stub_adapters import (
    StubFfmpegExtractAdapter,
    StubGameInputAdapter,
    StubObsCaptureAdapter,
)

__all__ = [
    "CaptureSourceConfig",
    "ExtractedFrame",
    "FfmpegExtractAdapter",
    "GameInputAdapter",
    "InputCommand",
    "InputCommandResult",
    "ObsCaptureAdapter",
    "PcGamePipelineResult",
    "PcGameStubPipeline",
    "RecordingSession",
    "StubFfmpegExtractAdapter",
    "StubGameInputAdapter",
    "StubObsCaptureAdapter",
]
