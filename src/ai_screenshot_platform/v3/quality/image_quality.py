from __future__ import annotations

from pathlib import Path


def basic_image_quality(path: str | Path) -> dict[str, object]:
    image_path = Path(path)
    if not image_path.is_file():
        return {"accepted": False, "reason": "file_missing"}
    if image_path.stat().st_size <= 0:
        return {"accepted": False, "reason": "empty_file"}
    pixel_quality = _pixel_quality(image_path)
    if pixel_quality is not None:
        return pixel_quality
    return {"accepted": True, "reason": "basic_file_check_passed", "bytes": image_path.stat().st_size}


def _pixel_quality(image_path: Path) -> dict[str, object] | None:
    try:
        from PIL import Image

        with Image.open(image_path) as image:
            sample = image.convert("L").resize((1, 1))
            mean = int(sample.getpixel((0, 0)))
            extrema = image.convert("L").getextrema()
    except Exception:
        return None
    details = {"bytes": image_path.stat().st_size, "mean_luma": mean, "luma_min": extrema[0], "luma_max": extrema[1]}
    if extrema[1] <= 5:
        return {"accepted": False, "reason": "black_screen", **details}
    if extrema[0] >= 250:
        return {"accepted": False, "reason": "white_screen", **details}
    return {"accepted": True, "reason": "pixel_check_passed", **details}
