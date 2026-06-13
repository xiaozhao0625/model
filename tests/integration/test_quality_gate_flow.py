from __future__ import annotations

import json

from ai_screenshot_platform.common.quality_gate.contracts import ScreenshotQualityInput
from ai_screenshot_platform.common.quality_gate.dataset_cleaner import DatasetCleaner


def test_quality_gate_flow_rejects_dangerous_and_keeps_clean(tmp_path):
    output = DatasetCleaner(tmp_path / "out").clean(
        [
            ScreenshotQualityInput(
                app_id="app",
                run_id="run",
                image_id="clean",
                image_bytes=b"abcdefg",
                platform_type="web",
                worker_type="web",
                content_area_only=True,
                metadata={"width": 1280, "height": 720},
            ),
            ScreenshotQualityInput(
                app_id="app",
                run_id="run",
                image_id="danger",
                image_bytes=b"danger",
                metadata={"width": 1280, "height": 720, "ocr_text": "支付 验证码"},
            ),
        ]
    )

    report = json.loads(output.quality_report_path.read_text(encoding="utf-8"))
    assert report["accepted_count"] == 1
    assert report["rejected_count"] == 1
