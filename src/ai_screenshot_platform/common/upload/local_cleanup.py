from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus


class LocalCleanupError(ValueError):
    pass


@dataclass(frozen=True)
class CleanupRecord:
    app_id: str
    run_id: str
    status: str
    local_path: str
    deleted_dirs: list[str]
    kept_files: list[str]
    deleted_file_count: int
    deleted_total_bytes: int
    cleaned_at: str
    confirmed_by: str

    def to_dict(self) -> dict[str, int | str | list[str]]:
        return asdict(self)


class LocalCleanupManager:
    cleanup_record_name = "cleanup_record.json"
    manifest_name = "upload_manifest.json"
    upload_record_name = "upload_record.json"
    deletable_dirs = ("fixed", "low", "high", "rejected", "temp_video")
    kept_files = (
        "summary.json",
        "meta.jsonl",
        "upload_manifest.json",
        "upload_record.json",
        "cleanup_record.json",
        "run.log",
    )

    def cleanup(
        self,
        run_dir: str | Path,
        current_status: RunStatus,
    ) -> dict[str, int | str | list[str]]:
        resolved_run_dir = Path(run_dir).resolve()
        cleanup_record_path = resolved_run_dir / self.cleanup_record_name
        if current_status == RunStatus.LOCAL_DELETED and cleanup_record_path.is_file():
            return json.loads(cleanup_record_path.read_text(encoding="utf-8"))

        if current_status != RunStatus.UPLOADED_CONFIRMED:
            raise LocalCleanupError("local cleanup requires uploaded_confirmed status")

        manifest_path = resolved_run_dir / self.manifest_name
        if not manifest_path.is_file():
            raise LocalCleanupError("upload_manifest.json is required before cleanup")

        upload_record_path = resolved_run_dir / self.upload_record_name
        if not upload_record_path.is_file():
            raise LocalCleanupError("upload_record.json is required before cleanup")

        upload_record = json.loads(upload_record_path.read_text(encoding="utf-8"))
        if upload_record.get("delete_allowed") is not True:
            raise LocalCleanupError("upload_record.json delete_allowed must be true")

        deleted_file_count, deleted_total_bytes = self._collect_deletion_stats(
            resolved_run_dir
        )
        deleted_dirs = self._delete_allowed_dirs(resolved_run_dir)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        record = CleanupRecord(
            app_id=str(manifest["app_id"]),
            run_id=str(manifest["run_id"]),
            status=RunStatus.LOCAL_DELETED.value,
            local_path=str(resolved_run_dir),
            deleted_dirs=deleted_dirs,
            kept_files=list(self.kept_files),
            deleted_file_count=deleted_file_count,
            deleted_total_bytes=deleted_total_bytes,
            cleaned_at=datetime.now(timezone.utc).isoformat(),
            confirmed_by=str(upload_record["confirmed_by"]),
        ).to_dict()
        cleanup_record_path.write_text(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return record

    def _collect_deletion_stats(self, run_dir: Path) -> tuple[int, int]:
        file_count = 0
        total_bytes = 0
        for directory_name in self.deletable_dirs:
            directory = self._safe_child(run_dir, directory_name)
            if not directory.exists():
                continue
            for path in directory.rglob("*"):
                if path.is_file():
                    file_count += 1
                    total_bytes += path.stat().st_size
        return file_count, total_bytes

    def _delete_allowed_dirs(self, run_dir: Path) -> list[str]:
        deleted_dirs: list[str] = []
        for directory_name in self.deletable_dirs:
            directory = self._safe_child(run_dir, directory_name)
            if directory.exists():
                shutil.rmtree(directory)
            deleted_dirs.append(directory_name)
        return deleted_dirs

    def _safe_child(self, run_dir: Path, child_name: str) -> Path:
        child = (run_dir / child_name).resolve()
        if not child.is_relative_to(run_dir):
            raise LocalCleanupError("cleanup path would escape run directory")
        return child
