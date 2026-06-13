from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.quality_gate.contracts import ScreenshotQualityInput  # noqa: E402
from ai_screenshot_platform.common.quality_gate.dataset_cleaner import DatasetCleaner  # noqa: E402


def main() -> None:
    output = DatasetCleaner(REPO_ROOT / "runs" / "dev_p125_quality_gate").clean(
        [
            ScreenshotQualityInput(
                app_id="demo",
                run_id="quality",
                image_id="clean",
                image_bytes=b"abcdef",
                platform_type="web",
                worker_type="web",
                content_area_only=True,
                metadata={"width": 1280, "height": 720},
            ),
            ScreenshotQualityInput(
                app_id="demo",
                run_id="quality",
                image_id="danger",
                image_bytes=b"danger",
                metadata={"width": 1280, "height": 720, "ocr_text": "验证码 支付"},
            ),
        ]
    )
    print(
        json.dumps(
            {
                "quality_report_path": str(output.quality_report_path),
                "clean_manifest_path": str(output.clean_manifest_path),
                "rejected_manifest_path": str(output.rejected_manifest_path),
                "ocr_report_path": str(output.ocr_report_path),
                "source_modified": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
