from __future__ import annotations

from ai_screenshot_platform.workers.android.adb_runtime import AdbRuntimeResult


class AndroidAppManager:
    def install_apk(self, profile) -> AdbRuntimeResult:
        if not profile.apk_path:
            return AdbRuntimeResult("unavailable", "apk_path_missing")
        return AdbRuntimeResult("skipped", "real_install_not_enabled")

    def launch_app(self, profile) -> AdbRuntimeResult:
        if not profile.app_package:
            return AdbRuntimeResult("unavailable", "package_missing")
        return AdbRuntimeResult("skipped", "real_launch_not_enabled")

    def stop_app(self, profile) -> AdbRuntimeResult:
        return AdbRuntimeResult("skipped", "real_stop_not_enabled")

    def clear_app_data(self, profile) -> AdbRuntimeResult:
        return AdbRuntimeResult("blocked", "clear_data_disabled_by_default")

    def grant_permissions(self, profile) -> AdbRuntimeResult:
        return AdbRuntimeResult("skipped", "permission_grant_requires_policy")
