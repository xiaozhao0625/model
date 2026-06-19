from __future__ import annotations

from ai_screenshot_platform.v3.model.registry import UiModelRegistry
from ai_screenshot_platform.v3.ocr.mock_provider import MockOcrProvider
from ai_screenshot_platform.v3.ocr.paddle_provider import PaddleOcrProvider
from ai_screenshot_platform.v3.schemas import V3Health, V3TaskConfig


def build_v3_health(model_registry: UiModelRegistry | None = None) -> V3Health:
    registry = model_registry or UiModelRegistry()
    ocr = [MockOcrProvider().health(), PaddleOcrProvider().health()]
    models = registry.health()
    ocr_ready = any(item.status == "ready" for item in ocr)
    showui_ready = any(item.provider == "showui" and item.status == "ready" and item.enabled for item in models)
    safety_ready = True
    return V3Health(
        status="ready" if ocr_ready and safety_ready else "degraded",
        ocr=ocr,
        models=models,
        complete_auto_mode_ready=ocr_ready and showui_ready and safety_ready,
        defaults=V3TaskConfig(),
    )
