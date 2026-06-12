from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus


class UploadManifestError(ValueError):
    pass


@dataclass(frozen=True)
class UploadManifest:
    app_id: str
    run_id: str
    status: str
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    local_path: str
    expected_upload_folder: str
    file_count: int
    total_bytes: int
    created_at: str
    delete_allowed_after_user_confirm: bool

    def to_dict(self) -> dict[str, int | str | bool]:
        return asdict(self)


class UploadManifestGenerator:
    manifest_name = "upload_manifest.json"

    def generate(
        self,
        run_dir: str | Path,
        expected_upload_folder: str,
        current_status: RunStatus,
    ) -> dict[str, int | str | bool]:
        if current_status != RunStatus.CAPTURE_COMPLETED:
            raise UploadManifestError(
                "upload_manifest.json can only be generated from capture_completed"
            )

        resolved_run_dir = Path(run_dir).resolve()
        summary_path = resolved_run_dir / "summary.json"
        if not summary_path.is_file():
            raise UploadManifestError("summary.json is required to generate manifest")

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        file_count, total_bytes = self._collect_file_stats(resolved_run_dir)
        manifest = UploadManifest(
            app_id=str(summary["app_id"]),
            run_id=str(summary["run_id"]),
            status=RunStatus.UPLOAD_PENDING.value,
            valid_total=int(summary["valid_total"]),
            fixed_count=int(summary["fixed_count"]),
            low_count=int(summary["low_count"]),
            high_count=int(summary["high_count"]),
            rejected_count=int(summary["rejected_count"]),
            local_path=str(resolved_run_dir),
            expected_upload_folder=expected_upload_folder,
            file_count=file_count,
            total_bytes=total_bytes,
            created_at=datetime.now(timezone.utc).isoformat(),
            delete_allowed_after_user_confirm=False,
        ).to_dict()

        manifest_path = resolved_run_dir / self.manifest_name
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest

    def _collect_file_stats(self, run_dir: Path) -> tuple[int, int]:
        file_count = 0
        total_bytes = 0
        for path in run_dir.rglob("*"):
            if not path.is_file() or path.name == self.manifest_name:
                continue
            file_count += 1
            total_bytes += path.stat().st_size
        return file_count, total_bytes
