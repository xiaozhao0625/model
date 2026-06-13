from __future__ import annotations

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.workers.pc_app.contracts import (
    PcAppCapturedFrame,
    PcAppCommand,
    PcAppCommandResult,
    PcAppTargetConfig,
)
from ai_screenshot_platform.workers.pc_app.health_check import check_pc_app_health
from ai_screenshot_platform.workers.runtime.health import ToolHealth


class RealPcAppWindowAdapter:
    def __init__(self, enabled: bool = False, capture_backend: str = "stub") -> None:
        self.enabled = enabled
        self.capture_backend = capture_backend

    def health(self) -> ToolHealth:
        if not self.enabled:
            return ToolHealth(
                name="pc_app_real_adapter",
                available=False,
                version=None,
                reason="disabled by config",
                required_for="pc app real capture smoke",
            )
        health = check_pc_app_health()
        if health["pywinauto"].available and (
            health.get(self.capture_backend) and health[self.capture_backend].available
        ):
            return ToolHealth(
                name="pc_app_real_adapter",
                available=True,
                version=None,
                reason=f"pywinauto and {self.capture_backend} are available",
                required_for="pc app real capture smoke",
            )
        return ToolHealth(
            name="pc_app_real_adapter",
            available=False,
            version=None,
            reason="required pc app optional modules are unavailable",
            required_for="pc app real capture smoke",
        )

    def focus_target(self, config: PcAppTargetConfig) -> PcAppCommandResult:
        health = self.health()
        if not health.available:
            return PcAppCommandResult(
                command_id=f"focus:{config.app_id}",
                executed=False,
                skipped=True,
                reason=health.reason,
            )
        import pywinauto

        app = pywinauto.Application().connect(title_re=config.window_title)
        app.top_window().set_focus()
        return PcAppCommandResult(
            command_id=f"focus:{config.app_id}",
            executed=True,
            skipped=False,
            reason="focused target window",
        )

    def execute(self, command: PcAppCommand) -> PcAppCommandResult:
        return PcAppCommandResult(
            command_id=command.command_id,
            executed=False,
            skipped=True,
            reason="real pc app adapter does not execute input commands in P10",
        )

    def capture_frame(self, config: PcAppTargetConfig) -> PcAppCapturedFrame:
        health = self.health()
        if not health.available:
            raise RuntimeError(f"pc app capture unavailable: {health.reason}")
        if self.capture_backend == "mss":
            import mss

            with mss.mss() as capture:
                shot = capture.grab(config.content_region)
                image_bytes = bytes(shot.rgb)
        elif self.capture_backend == "dxcam":
            import dxcam

            camera = dxcam.create()
            region = config.content_region
            frame = camera.grab(
                region=(
                    region["x"],
                    region["y"],
                    region["x"] + region["width"],
                    region["y"] + region["height"],
                )
            )
            image_bytes = frame.tobytes()
        else:
            raise RuntimeError(f"unsupported pc app capture backend: {self.capture_backend}")

        return PcAppCapturedFrame(
            frame_id=f"pc-app-real-{config.app_id}",
            image_bytes=image_bytes,
            bucket=config.bucket if isinstance(config.bucket, Bucket) else Bucket.LOW,
            source=f"pc_app_real_{self.capture_backend}:{config.content_region}",
        )
