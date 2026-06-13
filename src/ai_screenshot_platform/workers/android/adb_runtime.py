from __future__ import annotations

from dataclasses import dataclass
import shutil


@dataclass(frozen=True)
class AdbRuntimeResult:
    status: str
    reason: str | None = None
    output: str | None = None
    data: dict | None = None


class AdbRuntime:
    forbidden_shell_terms = {"su", "root", "pm clear"}

    def __init__(self, adb_path: str = "adb", timeout_seconds: int = 10) -> None:
        self.adb_path = adb_path
        self.timeout_seconds = timeout_seconds

    def check_adb_available(self) -> AdbRuntimeResult:
        if shutil.which(self.adb_path) is None:
            return AdbRuntimeResult("unavailable", "adb_unavailable")
        return AdbRuntimeResult("available")

    def list_devices(self) -> AdbRuntimeResult:
        if self.check_adb_available().status != "available":
            return AdbRuntimeResult("unavailable", "adb_unavailable", data={"devices": []})
        return AdbRuntimeResult("no_devices", "not_executed_in_default_path", data={"devices": []})

    def connect_device(self, profile) -> AdbRuntimeResult:
        if self.check_adb_available().status != "available":
            return AdbRuntimeResult("unavailable", "adb_unavailable")
        return AdbRuntimeResult("skipped", "real_connect_not_enabled")

    def get_device_state(self, serial: str) -> AdbRuntimeResult:
        if self.check_adb_available().status != "available":
            return AdbRuntimeResult("unavailable", "adb_unavailable")
        return AdbRuntimeResult("skipped", "real_state_not_enabled")

    def shell(self, serial: str, command: str) -> AdbRuntimeResult:
        normalized = command.lower()
        if any(term in normalized for term in self.forbidden_shell_terms):
            return AdbRuntimeResult("blocked", "privileged_command_blocked")
        if self.check_adb_available().status != "available":
            return AdbRuntimeResult("unavailable", "adb_unavailable")
        return AdbRuntimeResult("skipped", "real_shell_not_enabled")

    def screencap(self, serial: str) -> AdbRuntimeResult:
        if self.check_adb_available().status != "available":
            return AdbRuntimeResult("unavailable", "adb_unavailable")
        return AdbRuntimeResult("skipped", "real_screencap_not_enabled")

    def uiautomator_dump(self, serial: str) -> AdbRuntimeResult:
        if self.check_adb_available().status != "available":
            return AdbRuntimeResult("unavailable", "adb_unavailable")
        return AdbRuntimeResult("skipped", "real_ui_dump_not_enabled")

    def input_tap(self, serial: str, x: int, y: int) -> AdbRuntimeResult:
        return self.shell(serial, f"input tap {x} {y}")

    def input_swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration: int) -> AdbRuntimeResult:
        return self.shell(serial, f"input swipe {x1} {y1} {x2} {y2} {duration}")

    def input_keyevent(self, serial: str, keycode: int) -> AdbRuntimeResult:
        return self.shell(serial, f"input keyevent {keycode}")
