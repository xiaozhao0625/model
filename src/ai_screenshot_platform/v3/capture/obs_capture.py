from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObsCaptureConfig:
    host: str = "127.0.0.1"
    port: int = 4455
    source_name: str | None = None


class ObsCaptureAdapter:
    def __init__(self, config: ObsCaptureConfig | None = None) -> None:
        self.config = config or ObsCaptureConfig()

    def health(self) -> dict[str, object]:
        return {
            "provider": "obs",
            "status": "degraded",
            "reason": "OBS adapter skeleton present; real capture requires user-configured OBS websocket/source",
            "host": self.config.host,
            "port": self.config.port,
        }
