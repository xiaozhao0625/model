from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.domain.buckets import Bucket  # noqa: E402
from ai_screenshot_platform.common.runtime.run_session import (  # noqa: E402
    LocalRunSession,
    RunSessionConfig,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local mock P2 upload and cleanup session."
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--target-min", type=int, default=1000)
    parser.add_argument("--unique-count", type=int, default=3)
    parser.add_argument("--duplicate-count", type=int, default=0)
    parser.add_argument(
        "--bucket",
        choices=[Bucket.FIXED.value, Bucket.LOW.value, Bucket.HIGH.value],
        default=Bucket.LOW.value,
    )
    parser.add_argument("--confirmed-by", required=True)
    return parser.parse_args()


def run_mock(args: argparse.Namespace) -> dict[str, Any]:
    session = LocalRunSession(
        RunSessionConfig(
            root_dir=args.root,
            app_id=args.app_id,
            run_id=args.run_id,
            target_min=args.target_min,
        )
    )
    bucket = Bucket(args.bucket)
    expected_upload_folder = f"BaiduNetdisk:/screenshots/{args.app_id}/{args.run_id}"

    session.start()

    first_unique_bytes: bytes | None = None
    for index in range(args.unique_count):
        image_bytes = f"p2-mock-image-{index}".encode("utf-8")
        if first_unique_bytes is None:
            first_unique_bytes = image_bytes
        session.save_image(bucket, image_bytes)

    duplicate_bytes = first_unique_bytes or b"p2-mock-duplicate-source"
    for _ in range(args.duplicate_count):
        session.save_image(bucket, duplicate_bytes)

    session.evaluate_completion()
    summary = session.generate_summary()
    session.generate_upload_manifest(expected_upload_folder)
    session.confirm_uploaded(confirmed_by=args.confirmed_by)
    cleanup_record = session.cleanup_local_files()
    session.finalize_completed()

    return {
        "app_id": args.app_id,
        "run_id": args.run_id,
        "final_status": session.status.value,
        "valid_total": summary["valid_total"],
        "local_path": str(session.run_dir),
        "summary_path": str(session.store.summary_path),
        "meta_path": str(session.store.meta_path),
        "manifest_path": str(session.upload_manifest_path),
        "upload_record_path": str(session.upload_record_path),
        "cleanup_record_path": str(session.cleanup_record_path),
        "run_log_path": str(session.run_log_path),
        "deleted_dirs": cleanup_record["deleted_dirs"],
        "kept_files": cleanup_record["kept_files"],
    }


def main() -> None:
    print(json.dumps(run_mock(parse_args()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
