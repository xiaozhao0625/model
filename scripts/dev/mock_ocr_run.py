from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.ocr.contracts import OcrInput  # noqa: E402
from ai_screenshot_platform.common.ocr.router import OcrRouter  # noqa: E402


def main() -> None:
    router = OcrRouter.from_policy(
        {"default_provider": "mock", "mock_text": "验证码 支付 账号安全 发送聊天"}
    )
    result = router.run_ocr(OcrInput(image_bytes=b"mock"))
    print(
        json.dumps(
            {
                "provider": result.provider,
                "available": result.available,
                "risk_hits": [hit.risk_type for hit in result.risk_hits],
                "scene_hints": result.scene_hints,
                "real_ocr_used": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
