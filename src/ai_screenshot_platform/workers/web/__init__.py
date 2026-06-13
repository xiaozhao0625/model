from ai_screenshot_platform.workers.web.contracts import (
    WebAutomationAdapter,
    WebCapturedFrame,
    WebCommand,
    WebCommandResult,
    WebPipelineResult,
    WebTargetConfig,
)
from ai_screenshot_platform.workers.web.pipeline import WebStubPipeline
from ai_screenshot_platform.workers.web.stub_adapters import StubWebAutomationAdapter

__all__ = [
    "StubWebAutomationAdapter",
    "WebAutomationAdapter",
    "WebCapturedFrame",
    "WebCommand",
    "WebCommandResult",
    "WebPipelineResult",
    "WebStubPipeline",
    "WebTargetConfig",
]
