from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.ocr.contracts import OcrResult


@dataclass(frozen=True)
class ScreenshotQualityInput:
    app_id: str = ""
    run_id: str = ""
    image_id: str = ""
    image_path: Path | None = None
    image_bytes: bytes | None = None
    bucket: str = "low"
    capture_method: str | None = None
    platform_type: str | None = None
    worker_type: str | None = None
    source_window_title: str | None = None
    target_window_title: str | None = None
    content_area_only: bool = False
    expected_roi: dict[str, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    ocr_result: OcrResult | None = None


@dataclass(frozen=True)
class ScreenshotQualityResult:
    image_id: str
    accepted: bool
    reject_reason: str | None = None
    quality_score: float = 1.0
    is_black_screen: bool = False
    is_white_screen: bool = False
    is_blurry: bool = False
    is_wrong_window: bool = False
    has_browser_chrome: bool = False
    has_os_taskbar: bool = False
    has_title_bar: bool = False
    is_near_duplicate: bool = False
    resolution_ok: bool = True
    ocr_risk_hit_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
