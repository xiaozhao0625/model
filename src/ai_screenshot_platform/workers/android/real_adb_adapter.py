from __future__ import annotations

from ai_screenshot_platform.workers.android.contracts import (
    AndroidCapturedFrame,
    AndroidDeviceCommand,
    AndroidDeviceCommandResult,
    AndroidTargetConfig,
)
from ai_screenshot_platform.workers.android.health_check import check_android_adb_health
from ai_screenshot_platform.workers.runtime.health import ToolHealth


class RealAdbAndroidDeviceAdapter:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def health(self) -> ToolHealth:
        if not self.enabled:
            return ToolHealth(
                name="adb",
                available=False,
                version=None,
                reason="disabled by config",
                required_for="android real capture smoke",
            )
        return check_android_adb_health()

    def connect(self, config: AndroidTargetConfig) -> AndroidDeviceCommandResult:
        health = self.health()
        if not health.available:
            return AndroidDeviceCommandResult(
                command_id=f"connect:{config.device_id}",
                executed=False,
                skipped=True,
                reason=health.reason,
            )
        import subprocess

        subprocess.run(["adb", "-s", config.device_id, "get-state"], check=True)
        return AndroidDeviceCommandResult(
            command_id=f"connect:{config.device_id}",
            executed=True,
            skipped=False,
            reason="adb device is reachable",
        )

    def launch_app(self, config: AndroidTargetConfig) -> AndroidDeviceCommandResult:
        health = self.health()
        if not health.available:
            return AndroidDeviceCommandResult(
                command_id=f"launch:{config.package_name}",
                executed=False,
                skipped=True,
                reason=health.reason,
            )
        import subprocess

        subprocess.run(
            [
                "adb",
                "-s",
                config.device_id,
                "shell",
                "am",
                "start",
                "-n",
                f"{config.package_name}/{config.activity_name}",
            ],
            check=True,
        )
        return AndroidDeviceCommandResult(
            command_id=f"launch:{config.package_name}",
            executed=True,
            skipped=False,
            reason="adb launch command completed",
        )

    def execute(self, command: AndroidDeviceCommand) -> AndroidDeviceCommandResult:
        return AndroidDeviceCommandResult(
            command_id=command.command_id,
            executed=False,
            skipped=True,
            reason="real adb adapter does not execute arbitrary commands in P10",
        )

    def capture_frame(self, config: AndroidTargetConfig) -> AndroidCapturedFrame:
        health = self.health()
        if not health.available:
            raise RuntimeError(f"adb unavailable: {health.reason}")
        import subprocess

        completed = subprocess.run(
            ["adb", "-s", config.device_id, "exec-out", "screencap", "-p"],
            check=True,
            capture_output=True,
        )
        return AndroidCapturedFrame(
            frame_id=f"adb-android-{config.app_id}",
            image_bytes=completed.stdout,
            bucket=config.bucket,
            source="adb_screencap",
        )
