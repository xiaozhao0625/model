from __future__ import annotations

from pathlib import Path


def basic_image_quality(path: str | Path) -> dict[str, object]:
    image_path = Path(path)
    if not image_path.is_file():
        return {"accepted": False, "reason": "file_missing"}
    if image_path.stat().st_size <= 0:
        return {"accepted": False, "reason": "empty_file"}
    return {"accepted": True, "reason": "basic_file_check_passed", "bytes": image_path.stat().st_size}
