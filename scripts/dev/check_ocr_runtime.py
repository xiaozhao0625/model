from __future__ import annotations

import importlib.util
import json


def main() -> None:
    result = {
        "disabled_provider": "available",
        "mock_provider": "available",
        "paddleocr": "available" if importlib.util.find_spec("paddleocr") else "unavailable",
        "easyocr": "available" if importlib.util.find_spec("easyocr") else "unavailable",
        "gpu_required": False,
        "skipped_reason": "real_ocr_optional",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
