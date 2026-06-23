from __future__ import annotations

import json
import os
from pathlib import Path

from ai_screenshot_platform.v3.model.registry import UiModelRegistry
from ai_screenshot_platform.v3.ocr.mock_provider import MockOcrProvider
from ai_screenshot_platform.v3.ocr.paddle_provider import PaddleOcrProvider
from ai_screenshot_platform.v3.action.input_gateway import load_input_gateway_readiness
from ai_screenshot_platform.v3.schemas import ProviderHealth, V3Health, V3TaskConfig


def build_v3_health(model_registry: UiModelRegistry | None = None) -> V3Health:
    registry = model_registry or UiModelRegistry()
    ocr = [MockOcrProvider().health(), PaddleOcrProvider().health()]
    models = registry.health()
    ocr_ready = any(item.status == "ready" for item in ocr)
    showui_ready = any(item.provider == "showui" and item.status == "ready" and item.enabled for item in models)
    safety_ready = True
    ocr_readiness = _ocr_production_readiness(ocr)
    input_gateway = load_input_gateway_readiness()
    readiness_blockers = [*ocr_readiness["readiness_blockers"]]
    if not input_gateway.input_gateway_ready:
        readiness_blockers.extend(input_gateway.blockers)
    full_auto_ready = (
        ocr_ready
        and showui_ready
        and safety_ready
        and ocr_readiness["ocr_production_ready"]
        and input_gateway.input_gateway_ready
    )
    return V3Health(
        status=(
            "ready"
            if ocr_ready and safety_ready and ocr_readiness["ocr_production_ready"] and input_gateway.input_gateway_ready
            else "degraded"
        ),
        ocr=ocr,
        models=models,
        complete_auto_mode_ready=full_auto_ready,
        full_auto_capture_ready=full_auto_ready,
        ocr_gpu_ready=ocr_readiness["ocr_gpu_ready"],
        ocr_performance_ready=ocr_readiness["ocr_performance_ready"],
        ocr_production_ready=ocr_readiness["ocr_production_ready"],
        input_gateway_ready=input_gateway.input_gateway_ready,
        cursor_read_ready=input_gateway.cursor_read_ready,
        mouse_click_ready=input_gateway.mouse_click_ready,
        same_desktop_session_ready=input_gateway.same_desktop_session_ready,
        same_integrity_ready=input_gateway.same_integrity_ready,
        interactive_desktop_ready=input_gateway.interactive_desktop_ready,
        click_backend=input_gateway.click_backend,
        input_gateway_blockers=input_gateway.blockers,
        input_gateway_diagnosis_path=input_gateway.diagnosis_path,
        real_input_enabled=os.environ.get("APP_SHOT_ALLOW_REAL_INPUT", "").strip() == "1",
        readiness_blockers=readiness_blockers,
        ocr_performance=_ocr_performance_summary(),
        frame_pump=_frame_pump_summary(),
        power_policy=_power_policy_summary(),
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


def _ocr_performance_summary() -> dict[str, object]:
    report_path = _performance_report_path()
    report = _read_performance_report()
    timings = report.get("timings") if isinstance(report.get("timings"), dict) else {}
    summary = {
        "ready": bool(report.get("ocr_performance_ready") is True),
        "report_path": str(report_path) if report_path else None,
        "report_exists": bool(report),
        "full_frame_ms": _number_from(report, timings, "full_frame_ms"),
        "roi_ms": _number_from(report, timings, "roi_ms"),
        "scaled_ms": _number_from(report, timings, "scaled_ms"),
        "cache_hit_ms": _number_from(report, timings, "cache_hit_ms"),
        "failure_reasons": report.get("failure_reasons", []),
    }
    return summary


def _performance_report_path() -> Path | None:
    report_path = os.environ.get("APP_SHOT_OCR_PERFORMANCE_REPORT")
    if not report_path:
        app_shot_home = os.environ.get("APP_SHOT_HOME")
        if not app_shot_home:
            return None
        report_path = str(Path(app_shot_home) / "cache" / "ocr_gpu_performance.json")
    return Path(report_path)


def _number_from(report: dict[str, object], timings: dict[object, object], key: str) -> float | int | None:
    value = timings.get(key, report.get(key))
    return value if isinstance(value, (int, float)) else None


def _frame_pump_summary() -> dict[str, object]:
    path = _path_from_env_or_home("APP_SHOT_FRAME_PUMP_HEARTBEAT", "logs/frame_pump_heartbeat.json")
    payload = _read_json(path)
    return {
        "ready": bool(payload),
        "status": payload.get("status") if payload else "not_ready",
        "heartbeat_path": str(path) if path else None,
        "last_heartbeat": payload,
    }


def _power_policy_summary() -> dict[str, object]:
    active = _path_from_env_or_home("APP_SHOT_POWER_POLICY_ACTIVE", "logs/power_policy_capture_active.json")
    restored = _path_from_env_or_home("APP_SHOT_POWER_POLICY_RESTORED", "logs/power_policy_restored.json")
    before = _path_from_env_or_home("APP_SHOT_POWER_POLICY_BEFORE", "logs/power_policy_before_capture.json")
    active_payload = _read_json(active)
    restored_payload = _read_json(restored)
    active_mtime = active.stat().st_mtime if active and active.is_file() else 0
    restored_mtime = restored.stat().st_mtime if restored and restored.is_file() else 0
    status = "capture_active" if active_payload and active_mtime >= restored_mtime else "restored" if restored_payload else "unknown"
    return {
        "status": status,
        "active_path": str(active) if active else None,
        "restored_path": str(restored) if restored else None,
        "before_path": str(before) if before else None,
        "active": active_payload,
        "restored": restored_payload,
    }


def _path_from_env_or_home(env_name: str, relative_path: str) -> Path | None:
    configured = os.environ.get(env_name)
    if configured:
        return Path(configured)
    app_shot_home = os.environ.get("APP_SHOT_HOME")
    if not app_shot_home:
        return None
    return Path(app_shot_home) / Path(relative_path)


def _read_json(path: Path | None) -> dict[str, object]:
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
