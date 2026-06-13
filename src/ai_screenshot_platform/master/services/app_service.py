from __future__ import annotations

from ai_screenshot_platform.master.models.entities import AppRecord
from ai_screenshot_platform.master.repositories.app_repo import AppRepo


class AppService:
    def __init__(self, app_repo: AppRepo) -> None:
        self.app_repo = app_repo

    def create(self, app_id: str, name: str, type: str, platform: str) -> AppRecord:
        return self.app_repo.create(
            AppRecord(app_id=app_id, name=name, type=type, platform=platform)
        )

    def list(self) -> list[AppRecord]:
        return self.app_repo.list()

    def get(self, app_id: str) -> AppRecord:
        record = self.app_repo.get(app_id)
        if record is None:
            raise KeyError(f"app not found: {app_id}")
        return record
