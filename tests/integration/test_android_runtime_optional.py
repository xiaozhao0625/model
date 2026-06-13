from __future__ import annotations

from ai_screenshot_platform.workers.android.android_runtime_health import AndroidRuntimeHealthCheck


def test_android_runtime_optional_smoke_skips_without_adb():
    result = AndroidRuntimeHealthCheck(adb_path="definitely-missing-adb").check()

    assert result["adb_available"] is False
    assert result["skipped_reason"] == "adb_unavailable"
