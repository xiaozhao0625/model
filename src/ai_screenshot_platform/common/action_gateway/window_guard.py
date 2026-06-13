from __future__ import annotations


class WindowActionGuard:
    def is_target_window(self, source_title: str | None, target_title: str | None) -> bool:
        if not target_title:
            return True
        return bool(source_title and target_title.lower() in source_title.lower())
