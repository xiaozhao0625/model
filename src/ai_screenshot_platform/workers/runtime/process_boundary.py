from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerProcessBoundary:
    master_url: str
    once: bool = True
    transport: str = "http"

    def validate(self) -> None:
        if self.transport != "http":
            raise ValueError("P10 worker process boundary only supports http transport")
        if not self.master_url.startswith(("http://", "https://")):
            raise ValueError("master_url must be an HTTP URL")
