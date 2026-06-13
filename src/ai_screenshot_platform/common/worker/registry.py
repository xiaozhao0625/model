from __future__ import annotations

from ai_screenshot_platform.common.worker.contracts import (
    WorkerCapability,
    WorkerProfile,
    WorkerState,
)


class WorkerRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, WorkerProfile] = {}

    def register(self, profile: WorkerProfile) -> None:
        self._profiles[profile.worker_id] = profile

    def get(self, worker_id: str) -> WorkerProfile:
        return self._profiles[worker_id]

    def list_available(self) -> list[WorkerProfile]:
        return [
            profile
            for profile in self._profiles.values()
            if profile.enabled and profile.state == WorkerState.IDLE
        ]

    def find_by_capabilities(
        self,
        required_capabilities: set[WorkerCapability],
    ) -> list[WorkerProfile]:
        return [
            profile
            for profile in self.list_available()
            if required_capabilities.issubset(profile.capabilities)
        ]
