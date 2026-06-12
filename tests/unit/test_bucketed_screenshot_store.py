import json
from pathlib import Path

import pytest

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.completion_gate import CompletionGate
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.storage.screenshot_store import BucketedScreenshotStore


IMAGE_BYTES = b"fake-webp-bytes"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_initialization_creates_expected_directory_structure(tmp_path):
    store = BucketedScreenshotStore(tmp_path, app_id="demo_app", run_id="run_001")

    assert store.run_dir == tmp_path / "demo_app" / "run_001"
    for directory_name in ("fixed", "low", "high", "rejected", "temp_video"):
        assert (store.run_dir / directory_name).is_dir()


def test_save_low_image_writes_file_inside_bucket(tmp_path):
    store = BucketedScreenshotStore(tmp_path, app_id="demo_app", run_id="run_001")

    result = store.save_image(Bucket.LOW, IMAGE_BYTES)

    assert result.saved is True
    assert result.reason == "saved"
    assert (store.run_dir / result.meta["path"]).is_file()
    assert result.meta["path"] == "low/00000001.webp"


def test_save_high_image_appends_meta_jsonl_record(tmp_path):
    store = BucketedScreenshotStore(tmp_path, app_id="demo_app", run_id="run_001")

    result = store.save_image(Bucket.HIGH, IMAGE_BYTES)

    records = read_jsonl(store.meta_path)
    assert records == [result.meta]
    assert records[0]["image_id"] == "00000001"
    assert records[0]["app_id"] == "demo_app"
    assert records[0]["run_id"] == "run_001"
    assert records[0]["bucket"] == "high"
    assert records[0]["path"] == "high/00000001.webp"
    assert records[0]["valid"] is True
    assert records[0]["reject_reason"] is None
    assert isinstance(records[0]["timestamp"], str)


def test_save_rejected_increments_rejected_count_without_valid_total(tmp_path):
    store = BucketedScreenshotStore(tmp_path, app_id="demo_app", run_id="run_001")

    result = store.save_image(
        Bucket.REJECTED,
        IMAGE_BYTES,
        reject_reason="duplicate",
    )
    summary = store.generate_summary()

    assert result.meta["valid"] is False
    assert result.meta["reject_reason"] == "duplicate"
    assert summary["rejected_count"] == 1
    assert summary["valid_total"] == 0


def test_generate_summary_writes_expected_counts(tmp_path):
    store = BucketedScreenshotStore(tmp_path, app_id="demo_app", run_id="run_001")

    store.save_image(Bucket.FIXED, IMAGE_BYTES)
    store.save_image(Bucket.LOW, IMAGE_BYTES)
    store.save_image(Bucket.HIGH, IMAGE_BYTES)
    store.save_image(Bucket.REJECTED, IMAGE_BYTES, reject_reason="blurred")

    summary = store.generate_summary()
    summary_file = json.loads(store.summary_path.read_text(encoding="utf-8"))

    assert summary == summary_file
    assert summary == {
        "app_id": "demo_app",
        "run_id": "run_001",
        "fixed_count": 1,
        "low_count": 1,
        "high_count": 1,
        "rejected_count": 1,
        "valid_total": 3,
    }


def test_fixed_over_10_is_rejected_without_writing_extra_file(tmp_path):
    store = BucketedScreenshotStore(tmp_path, app_id="demo_app", run_id="run_001")

    for _ in range(10):
        assert store.save_image(Bucket.FIXED, IMAGE_BYTES).saved is True
    result = store.save_image(Bucket.FIXED, IMAGE_BYTES)

    assert result.saved is False
    assert result.reason == "fixed_cap_exceeded"
    assert result.meta is None
    assert len(list((store.run_dir / "fixed").glob("*.webp"))) == 10
    assert store.generate_summary()["fixed_count"] == 10


def test_illegal_bucket_is_rejected(tmp_path):
    store = BucketedScreenshotStore(tmp_path, app_id="demo_app", run_id="run_001")

    with pytest.raises(ValueError, match="unsupported bucket"):
        store.save_image("other", IMAGE_BYTES)


def test_path_escape_in_run_identity_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="path escape"):
        BucketedScreenshotStore(tmp_path, app_id="..", run_id="run_001")

    with pytest.raises(ValueError, match="path escape"):
        BucketedScreenshotStore(tmp_path, app_id="demo_app", run_id="../run_001")


def test_completion_gate_accepts_1000_low_images_from_store_summary(tmp_path):
    store = BucketedScreenshotStore(tmp_path, app_id="demo_app", run_id="run_001")

    for _ in range(1000):
        store.save_image(Bucket.LOW, IMAGE_BYTES)
    summary = store.generate_summary()
    decision = CompletionGate().evaluate(store.capture_counts())

    assert summary["low_count"] == 1000
    assert summary["valid_total"] == 1000
    assert decision.next_status == RunStatus.CAPTURE_COMPLETED
