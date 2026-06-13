from __future__ import annotations

from ai_screenshot_platform.workers.android.adb_runtime import AdbRuntime


def test_adb_runtime_is_unavailable_when_binary_missing():
    runtime = AdbRuntime(adb_path="definitely-missing-adb")

    assert runtime.check_adb_available().status == "unavailable"
    assert runtime.list_devices().status in {"unavailable", "no_devices"}


def test_adb_runtime_rejects_privileged_shell_commands():
    result = AdbRuntime(adb_path="definitely-missing-adb").shell("serial", "su root")

    assert result.status == "blocked"
    assert result.reason == "privileged_command_blocked"
