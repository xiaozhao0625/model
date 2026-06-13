from __future__ import annotations

import json

from ai_screenshot_platform.common.quality_gate.contracts import ScreenshotQualityInput
from ai_screenshot_platform.common.quality_gate.dataset_cleaner import DatasetCleaner


def test_dataset_cleaner_writes_reports_without_modifying_source(tmp_path):
    source = tmp_path / "run" / "high" / "0001.webp"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"not-black")
    original = source.read_bytes()

    output = DatasetCleaner(tmp_path / "quality_output").clean(
        [
            ScreenshotQualityInput(
                app_id="app",
                run_id="run",
                image_id="img1",
                image_path=source,
                image_bytes=b"not-black",
                bucket="high",
                metadata={"width": 1280, "height": 720},
            )
        ]
    )

    assert source.read_bytes() == original
    assert output.quality_report_path.exists()
    assert output.clean_manifest_path.exists()
    assert output.ocr_report_path.exists()
    report = json.loads(output.quality_report_path.read_text(encoding="utf-8"))
    assert report["accepted_count"] == 1
