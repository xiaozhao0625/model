from __future__ import annotations

from ai_screenshot_platform.workers.android.contracts import (
    AndroidCapturedFrame,
    AndroidDeviceCommand,
    AndroidDeviceCommandResult,
    AndroidQualityResult,
    AndroidTargetConfig,
    AndroidUiObservation,
)


class StubAndroidDeviceAdapter:
    def connect(self, config: AndroidTargetConfig) -> AndroidDeviceCommandResult:
        return AndroidDeviceCommandResult(
            command_id=f"connect:{config.device_id}",
            executed=False,
            skipped=True,
            reason="stub adapter skipped real adb connect",
        )

    def launch_app(self, config: AndroidTargetConfig) -> AndroidDeviceCommandResult:
        return AndroidDeviceCommandResult(
            command_id=f"launch:{config.package_name}",
            executed=False,
            skipped=True,
            reason="stub adapter skipped real android launch",
        )

    def execute(
        self,
        command: AndroidDeviceCommand,
    ) -> AndroidDeviceCommandResult:
        return AndroidDeviceCommandResult(
            command_id=command.command_id,
            executed=False,
            skipped=True,
            reason="stub adapter skipped real android command",
        )

    def capture_frame(self, config: AndroidTargetConfig) -> AndroidCapturedFrame:
        return AndroidCapturedFrame(
            frame_id=f"android-stub-{config.app_id}",
            image_bytes=(
                f"android_stub:{config.app_id}:{config.package_name}:"
                f"{config.activity_name}:{config.device_id}"
            ).encode("utf-8"),
            bucket=config.bucket,
            source="android_stub",
        )


class StubAndroidUiObserverAdapter:
    def observe(self, config: AndroidTargetConfig) -> AndroidUiObservation:
        return AndroidUiObservation(
            app_id=config.app_id,
            package_name=config.package_name,
            activity_name=config.activity_name,
            source="android_ui_stub",
            elements=[
                {
                    "id": "mock-root",
                    "text": "Mock Android UI",
                    "bounds": [0, 0, 1080, 1920],
                }
            ],
        )


class StubAndroidQualityAdapter:
    def check(self, frame: AndroidCapturedFrame) -> AndroidQualityResult:
        return AndroidQualityResult(
            valid=True,
            reason="stub_quality_valid",
        )
