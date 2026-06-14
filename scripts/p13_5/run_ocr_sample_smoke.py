from __future__ import annotations

import json


def main() -> int:
    print(
        json.dumps(
            {
                "schema_version": "p13.5.0",
                "status": "planned_only",
                "samples_processed": 0,
                "ocr_installed": False,
                "model_downloaded": False,
                "next_action": "Run only after user confirms P13.5.1 OCR installation.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
