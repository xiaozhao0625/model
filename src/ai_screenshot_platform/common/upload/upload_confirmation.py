from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus


class UploadConfirmationError(ValueError):
    pass


@dataclass(frozen=True)
class UploadRecord:
    app_id: str
    run_id: str
    status: str
    local_path: str
    expected_upload_folder: str
    actual_upload_folder: str
    confirmed_by: str
    confirmed_at: str
    manifest_path: str
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    delete_allowed: bool

    def to_dict(self) -> dict[str, int | str | bool]:
        return asdict(self)


class UploadConfirmationManager:
    record_name = "upload_record.json"
    manifest_name = "upload_manifest.json"

    def confirm(
        self,
        run_dir: str | Path,
        current_status: RunStatus,
        confirmed_by: str,
        actual_upload_folder: str | None = None,
    ) -> dict[str, int | str | bool]:
        if current_status != RunStatus.UPLOAD_PENDING:
            raise UploadConfirmationError(
                "upload confirmation requires upload_pending status"
            )

        resolved_run_dir = Path(run_dir).resolve()
        manifest_path = resolved_run_dir / self.manifest_name
        if not manifest_path.is_file():
            raise UploadConfirmationError(
                "upload_manifest.json is required to confirm upload"
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_upload_folder = str(manifest["expected_upload_folder"])
        record = UploadRecord(
            app_id=str(manifest["app_id"]),
            run_id=str(manifest["run_id"]),
            status=RunStatus.UPLOADED_CONFIRMED.value,
            local_path=str(manifest["local_path"]),
            expected_upload_folder=expected_upload_folder,
            actual_upload_folder=actual_upload_folder or expected_upload_folder,
            confirmed_by=confirmed_by,
            confirmed_at=datetime.now(timezone.utc).isoformat(),
            manifest_path=str(manifest_path),
            valid_total=int(manifest["valid_total"]),
            fixed_count=int(manifest["fixed_count"]),
            low_count=int(manifest["low_count"]),
            high_count=int(manifest["high_count"]),
            rejected_count=int(manifest["rejected_count"]),
            delete_allowed=True,
        ).to_dict()

        record_path = resolved_run_dir / self.record_name
        record_path.write_text(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return record
