from __future__ import annotations

from ai_screenshot_platform.workers.android.adb_runtime import AdbRuntime


class AndroidScreenshotCapture:
    def __init__(self, runtime: AdbRuntime | None = None) -> None:
        self.runtime = runtime or AdbRuntime()

    def capture_png(self, serial: str):
        return self.runtime.screencap(serial)
