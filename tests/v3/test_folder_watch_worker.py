from pathlib import Path

from ai_screenshot_platform.v3.capture.folder_watch_worker import run_folder_watch_loop, run_folder_watch_once
from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import OcrResult, OcrTextBox, ProviderHealth, V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore


class StaticOcrProvider(OcrProvider):
    provider_name = "static"

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=True)

    def recognize(self, image_path: str) -> OcrResult:
        return OcrResult(
            provider=self.provider_name,
            status="ok",
            text_boxes=[OcrTextBox(text="Start", bbox=[0, 0, 20, 20], confidence=0.9)],
        )


class FailingRuntime(V3Runtime):
    def ingest_image(self, run_id: str, image_path: str):
        if "bad" in image_path:
            raise RuntimeError("boom")
        return super().ingest_image(run_id, image_path)


def test_folder_watch_worker_processes_images_and_writes_summary(tmp_path):
    folder = tmp_path / "watch"
    folder.mkdir()
    first = folder / "first.png"
    second = folder / "second.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    runtime = V3Runtime(store=V3RunStore(tmp_path / "runs"), ocr_provider=StaticOcrProvider())
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True, save_root=str(tmp_path / "runs")))

    stats = run_folder_watch_once(runtime, run.run_id, folder)

    assert stats["discovered"] == 2
    assert stats["processed"] == 2
    assert stats["failed"] == 0
    assert stats["avg_ingest_ms"] >= 0
    assert len(runtime.images(run.run_id)) == 2
    assert (tmp_path / "runs" / run.run_id / "meta" / "folder_watch_summary.json").is_file()


def test_folder_watch_worker_keeps_going_after_ingest_failure(tmp_path):
    folder = tmp_path / "watch"
    folder.mkdir()
    bad = folder / "bad.png"
    good = folder / "good.png"
    bad.write_bytes(b"bad")
    good.write_bytes(b"good")
    seen: set[str] = set()
    runtime = FailingRuntime(store=V3RunStore(tmp_path / "runs"), ocr_provider=StaticOcrProvider())
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True, save_root=str(tmp_path / "runs")))

    stats = run_folder_watch_once(runtime, run.run_id, folder, seen=seen)
    second = run_folder_watch_once(runtime, run.run_id, folder, seen=seen)

    assert stats["discovered"] == 2
    assert stats["processed"] == 1
    assert stats["failed"] == 1
    assert stats["failures"][0]["image"].endswith("bad.png")
    assert second["discovered"] == 0
    assert len(runtime.images(run.run_id)) == 1


def test_folder_watch_loop_accumulates_iterations_and_summary(tmp_path):
    folder = tmp_path / "watch"
    folder.mkdir()
    image = folder / "first.png"
    image.write_bytes(b"first")
    runtime = V3Runtime(store=V3RunStore(tmp_path / "runs"), ocr_provider=StaticOcrProvider())
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True, save_root=str(tmp_path / "runs")))

    stats = run_folder_watch_loop(
        runtime,
        run.run_id,
        folder,
        poll_interval_seconds=0,
        max_iterations=2,
    )

    assert stats["iterations"] == 2
    assert stats["discovered"] == 1
    assert stats["processed"] == 1
    assert stats["failed"] == 0
    assert stats["stopped_reason"] == "max_iterations"
    assert (tmp_path / "runs" / run.run_id / "meta" / "folder_watch_summary.json").is_file()


def test_folder_watch_loop_retries_failures_before_quarantine(tmp_path):
    folder = tmp_path / "watch"
    folder.mkdir()
    bad = folder / "bad.png"
    bad.write_bytes(b"bad")
    runtime = FailingRuntime(store=V3RunStore(tmp_path / "runs"), ocr_provider=StaticOcrProvider())
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True, save_root=str(tmp_path / "runs")))

    stats = run_folder_watch_loop(
        runtime,
        run.run_id,
        folder,
        poll_interval_seconds=0,
        max_iterations=2,
        max_retries=1,
    )

    assert stats["iterations"] == 2
    assert stats["discovered"] == 2
    assert stats["processed"] == 0
    assert stats["failed"] == 2
    assert stats["quarantined"] == 1
    assert stats["seen"] == 1
