from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AndroidReuseMapping:
    entries: dict[str, str]

    @classmethod
    def default(cls) -> "AndroidReuseMapping":
        return cls(
            entries={
                "ADB 控制": "AndroidDeviceAdapter",
                "OCR Adapter": "future common/ocr",
                "UIAutomator 解析": "AndroidUiObserverAdapter",
                "QualityChecker": "AndroidQualityAdapter",
                "DuplicateChecker": "common quality/dedup",
                "StateManager": "LocalRunSession / meta.jsonl recovery",
                "ScreenshotManager": "BucketedScreenshotStore",
            }
        )

    def target_for(self, source_module: str) -> str:
        return self.entries[source_module]
