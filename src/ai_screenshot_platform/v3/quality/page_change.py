from __future__ import annotations


def page_changed(previous_sha256: str | None, current_sha256: str | None) -> bool:
    return bool(previous_sha256 and current_sha256 and previous_sha256 != current_sha256)
