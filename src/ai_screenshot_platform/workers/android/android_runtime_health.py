from __future__ import annotations

from ai_screenshot_platform.workers.android.adb_runtime import AdbRuntime


class AndroidRuntimeHealthCheck:
    def __init__(self, adb_path: str = "adb") -> None:
        self.runtime = AdbRuntime(adb_path=adb_path)

    def check(self) -> dict:
        available = self.runtime.check_adb_available()
        if available.status != "available":
            return {
                "adb_available": False,
                "devices": [],
                "selected_device": None,
                "screencap_status": "skipped",
                "ui_dump_status": "skipped",
                "ocr_fallback_status": "skipped",
                "input_status": "disabled",
                "skipped_reason": "adb_unavailable",
            }
        devices = self.runtime.list_devices()
        return {
            "adb_available": True,
            "devices": devices.data.get("devices", []) if devices.data else [],
            "selected_device": None,
            "screencap_status": "skipped",
            "ui_dump_status": "skipped",
            "ocr_fallback_status": "skipped",
            "input_status": "disabled",
            "skipped_reason": "no_devices",
        }
