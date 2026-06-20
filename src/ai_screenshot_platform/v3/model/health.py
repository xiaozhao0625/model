from __future__ import annotations

import json
import os
from pathlib import Path

from ai_screenshot_platform.v3.model.registry import UiModelRegistry
from ai_screenshot_platform.v3.ocr.mock_provider import MockOcrProvider
from ai_screenshot_platform.v3.ocr.paddle_provider import PaddleOcrProvider
from ai_screenshot_platform.v3.schemas import ProviderHealth, V3Health, V3TaskConfig


def build_v3_health(model_registry: UiModelRegistry | None = None) -> V3Health:
    registry = model_registry or UiModelRegistry()
    ocr = [MockOcrProvider().health(), PaddleOcrProvider().health()]
    models = registry.health()
    ocr_ready = any(item.status == "ready" for item in ocr)
    showui_ready = any(item.provider == "showui" and item.status == "ready" and item.enabled for item in models)
    safety_ready = True
    ocr_readiness = _ocr_production_readiness(ocr)
    full_auto_ready = ocr_ready and showui_ready and safety_ready and ocr_readiness["ocr_production_ready"]
    return V3Health(
        status="ready" if ocr_ready and safety_ready and ocr_readiness["ocr_production_ready"] else "degraded",
        ocr=ocr,
        models=models,
        complete_auto_mode_ready=full_auto_ready,
        full_auto_capture_ready=full_auto_ready,
        ocr_gpu_ready=ocr_readiness["ocr_gpu_ready"],
        ocr_performance_ready=ocr_readiness["ocr_performance_ready"],
        ocr_production_ready=ocr_readiness["ocr_production_ready"],
        readiness_blockers=ocr_readiness["readiness_blockers"],
        defaults=V3TaskConfig(),
    )


def _ocr_production_readiness(ocr_health: list[ProviderHealth]) -> dict[str, object]:
    paddle = next((item for item in ocr_health if item.provider == "paddleocr"), None)
    ocr_gpu_ready = bool(
        paddle
        and paddle.status == "ready"
        and paddle.enabled
        and paddle.details.get("compiled_cuda") is True
        and paddle.details.get("gpu_device") is True
    )
    report = _read_performance_report()
    ocr_performance_ready = bool(report.get("ocr_performance_ready") is True)
    blockers: list[str] = []
    if not ocr_gpu_ready:
        blockers.append("ocr_gpu_not_ready")
    if not report:
        blockers.append("ocr_performance_not_measured")
    elif not ocr_performance_ready:
        blockers.append("ocr_performance_not_ready")
    return {
        "ocr_gpu_ready": ocr_gpu_ready,
        "ocr_performance_ready": ocr_performance_ready,
        "ocr_production_ready": ocr_gpu_ready and ocr_performance_ready,
        "readiness_blockers": blockers,
    }


def _read_performance_report() -> dict[str, object]:
    report_path = os.environ.get("APP_SHOT_OCR_PERFORMANCE_REPORT")
    if not report_path:
        app_shot_home = os.environ.get("APP_SHOT_HOME")
        if not app_shot_home:
            return {}
        report_path = str(Path(app_shot_home) / "cache" / "ocr_gpu_performance.json")
    path = Path(report_path)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
