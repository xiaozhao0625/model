from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.completion_gate import CaptureCounts
from ai_screenshot_platform.common.quality.dedup import ContentHashDedupIndex


@dataclass(frozen=True)
class SaveImageResult:
    saved: bool
    reason: str
    meta: dict[str, Any] | None = None
    valid: bool = False
    duplicate_of: str | None = None


class BucketedScreenshotStore:
    BUCKET_DIRS = (Bucket.FIXED, Bucket.LOW, Bucket.HIGH, Bucket.REJECTED)

    def __init__(
        self,
        root_dir: str | Path,
        app_id: str,
        run_id: str,
        fixed_cap: int = 10,
    ) -> None:
        if fixed_cap < 0:
            raise ValueError("fixed_cap must be non-negative")

        self.root_dir = Path(root_dir).resolve()
        self.app_id = self._validate_path_part(app_id, "app_id")
        self.run_id = self._validate_path_part(run_id, "run_id")
        self.fixed_cap = fixed_cap
        self.run_dir = (self.root_dir / self.app_id / self.run_id).resolve()
        self._ensure_inside_root(self.run_dir)

        self.meta_path = self.run_dir / "meta.jsonl"
        self.summary_path = self.run_dir / "summary.json"
        self._next_image_number = 1
        self._counts = {
            Bucket.FIXED: 0,
            Bucket.LOW: 0,
            Bucket.HIGH: 0,
            Bucket.REJECTED: 0,
        }
        self._dedup_index = ContentHashDedupIndex()

        self._create_directories()

    def save_image(
        self,
        bucket: Bucket | str,
        image_bytes: bytes,
        reject_reason: str | None = None,
    ) -> SaveImageResult:
        parsed_bucket = self._parse_bucket(bucket)
        if not isinstance(image_bytes, bytes):
            raise TypeError("image_bytes must be bytes")
        if parsed_bucket == Bucket.FIXED and self._counts[Bucket.FIXED] >= self.fixed_cap:
            return SaveImageResult(
                saved=False,
                reason="fixed_cap_exceeded",
                meta=None,
                valid=False,
                duplicate_of=None,
            )

        content_hash = ContentHashDedupIndex.calculate_hash(image_bytes)
        dedup_result = self._dedup_index.check(content_hash)
        if dedup_result.is_duplicate:
            return SaveImageResult(
                saved=False,
                reason="duplicate_content_hash",
                meta=None,
                valid=False,
                duplicate_of=dedup_result.duplicate_of,
            )

        image_id = f"{self._next_image_number:08d}"
        relative_path = Path(parsed_bucket.value) / f"{image_id}.webp"
        absolute_path = (self.run_dir / relative_path).resolve()
        self._ensure_inside_run_dir(absolute_path)

        absolute_path.write_bytes(image_bytes)
        self._next_image_number += 1
        self._counts[parsed_bucket] += 1
        self._dedup_index.register(content_hash, image_id)

        meta = {
            "image_id": image_id,
            "app_id": self.app_id,
            "run_id": self.run_id,
            "bucket": parsed_bucket.value,
            "path": relative_path.as_posix(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "valid": parsed_bucket != Bucket.REJECTED,
            "reject_reason": reject_reason if parsed_bucket == Bucket.REJECTED else None,
            "content_hash": content_hash,
            "duplicate_of": None,
        }
        self._append_meta(meta)
        return SaveImageResult(
            saved=True,
            reason="saved",
            meta=meta,
            valid=parsed_bucket != Bucket.REJECTED,
            duplicate_of=None,
        )

    def generate_summary(self) -> dict[str, int | str]:
        summary: dict[str, int | str] = {
            "app_id": self.app_id,
            "run_id": self.run_id,
            "fixed_count": self._counts[Bucket.FIXED],
            "low_count": self._counts[Bucket.LOW],
            "high_count": self._counts[Bucket.HIGH],
            "rejected_count": self._counts[Bucket.REJECTED],
            "valid_total": self._valid_total(),
        }
        self.summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return summary

    def capture_counts(self) -> CaptureCounts:
        return CaptureCounts(
            fixed=self._counts[Bucket.FIXED],
            low=self._counts[Bucket.LOW],
            high=self._counts[Bucket.HIGH],
            rejected=self._counts[Bucket.REJECTED],
        )

    def _create_directories(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        for bucket in self.BUCKET_DIRS:
            (self.run_dir / bucket.value).mkdir(exist_ok=True)
        (self.run_dir / "temp_video").mkdir(exist_ok=True)

    def _append_meta(self, meta: dict[str, Any]) -> None:
        with self.meta_path.open("a", encoding="utf-8", newline="\n") as meta_file:
            meta_file.write(json.dumps(meta, ensure_ascii=False, sort_keys=True))
            meta_file.write("\n")

    def _valid_total(self) -> int:
        return (
            self._counts[Bucket.FIXED]
            + self._counts[Bucket.LOW]
            + self._counts[Bucket.HIGH]
        )

    def _parse_bucket(self, bucket: Bucket | str) -> Bucket:
        if isinstance(bucket, Bucket):
            return bucket
        try:
            return Bucket(bucket)
        except ValueError as exc:
            raise ValueError(f"unsupported bucket: {bucket}") from exc

    def _validate_path_part(self, value: str, field_name: str) -> str:
        if not value:
            raise ValueError(f"{field_name} must not be empty")
        if value in {".", ".."}:
            raise ValueError(f"{field_name} would cause path escape")
        path = Path(value)
        if path.is_absolute() or len(path.parts) != 1:
            raise ValueError(f"{field_name} would cause path escape")
        return value

    def _ensure_inside_root(self, path: Path) -> None:
        if not path.is_relative_to(self.root_dir):
            raise ValueError("run directory would escape root_dir")

    def _ensure_inside_run_dir(self, path: Path) -> None:
        if not path.is_relative_to(self.run_dir):
            raise ValueError("save path would escape run directory")
