from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_screenshot_platform.model_gateway.model_paths import ModelPathResolver


@dataclass(frozen=True)
class ModelDownloadPlanItem:
    model_id: str
    display_name: str
    target_path: Path
    download_url_or_hint: str
    enabled_by_default: bool
    load_mode: str
    estimated_action: str
    gpu_required: bool


class ModelDownloadPlanner:
    def __init__(self, manifest_path: str | Path) -> None:
        self.resolver = ModelPathResolver(manifest_path)

    def plan(self) -> list[ModelDownloadPlanItem]:
        items: list[ModelDownloadPlanItem] = []
        for info in self.resolver.resolve_all():
            entry = info.entry
            items.append(
                ModelDownloadPlanItem(
                    model_id=entry.model_id,
                    display_name=entry.display_name,
                    target_path=info.local_path,
                    download_url_or_hint=str(entry.download.get("url_or_hint", "")),
                    enabled_by_default=entry.enabled_by_default,
                    load_mode=entry.load_mode,
                    estimated_action="manual_download_required"
                    if info.missing_files
                    else "already_present",
                    gpu_required=entry.gpu_required,
                )
            )
        return items
