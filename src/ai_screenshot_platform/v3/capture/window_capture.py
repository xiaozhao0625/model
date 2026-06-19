from __future__ import annotations


class WindowCaptureAdapter:
    def health(self) -> dict[str, object]:
        return {
            "provider": "window_capture",
            "status": "degraded",
            "reason": "window capture adapter skeleton present; real capture must be enabled explicitly",
        }
