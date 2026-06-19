from __future__ import annotations

from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def list_new_images(folder: str | Path, seen: set[str] | None = None) -> list[Path]:
    root = Path(folder)
    seen = seen or set()
    if not root.is_dir():
        return []
    return [
        path
        for path in sorted(root.iterdir())
        if path.suffix.lower() in IMAGE_EXTENSIONS and str(path.resolve()) not in seen
    ]
