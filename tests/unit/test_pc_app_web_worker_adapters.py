from pathlib import Path

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.workers.pc_app.contracts import (
    PcAppCommand,
    PcAppTargetConfig,
)
from ai_screenshot_platform.workers.pc_app.pipeline import PcAppStubPipeline
from ai_screenshot_platform.workers.pc_app.stub_adapters import (
    StubPcAppAutomationAdapter,
)
from ai_screenshot_platform.workers.web.contracts import WebCommand, WebTargetConfig
from ai_screenshot_platform.workers.web.pipeline import WebStubPipeline
from ai_screenshot_platform.workers.web.stub_adapters import StubWebAutomationAdapter


def make_session(tmp_path, app_id="demo_app", run_id="run_001", target_min=3):
    return LocalRunSession(
        RunSessionConfig(
            root_dir=tmp_path,
            app_id=app_id,
            run_id=run_id,
            target_min=target_min,
        )
    )


def make_pc_app_config():
    return PcAppTargetConfig(
        app_id="desktop_editor",
        window_title="Mock Editor",
        process_name="editor.exe",
        content_region={"x": 10, "y": 20, "width": 800, "height": 600},
    )


def make_web_config():
    return WebTargetConfig(
        app_id="web_dashboard",
        url="https://example.invalid/dashboard",
        viewport_width=1280,
        viewport_height=720,
    )


def test_stub_pc_app_focus_target_does_not_execute_real_action():
    result = StubPcAppAutomationAdapter().focus_target(make_pc_app_config())

    assert result.executed is False
    assert result.skipped is True
    assert "stub" in result.reason


def test_stub_pc_app_capture_frame_returns_mock_frame():
    frame = StubPcAppAutomationAdapter().capture_frame(make_pc_app_config())

    assert frame.frame_id
    assert frame.image_bytes
    assert frame.bucket == Bucket.LOW
    assert frame.source == "pc_app_stub"


def test_pc_app_stub_pipeline_enters_capture_completed(tmp_path):
    pipeline = PcAppStubPipeline(
        session=make_session(tmp_path),
        automation_adapter=StubPcAppAutomationAdapter(),
    )

    result = pipeline.run(make_pc_app_config())

    assert result.status == RunStatus.CAPTURE_COMPLETED
    assert result.valid_total == 3


def test_pc_app_stub_pipeline_saves_low_bucket_images(tmp_path):
    pipeline = PcAppStubPipeline(
        session=make_session(tmp_path),
        automation_adapter=StubPcAppAutomationAdapter(),
    )

    result = pipeline.run(make_pc_app_config())

    assert result.low_count == 3
    assert result.high_count == 0


def test_stub_web_open_target_does_not_open_real_browser():
    result = StubWebAutomationAdapter().open_target(make_web_config())

    assert result.executed is False
    assert result.skipped is True
    assert "stub" in result.reason


def test_stub_web_capture_frame_returns_content_area_only_mock_frame():
    frame = StubWebAutomationAdapter().capture_frame(make_web_config())

    assert frame.frame_id
    assert frame.image_bytes
    assert frame.bucket == Bucket.LOW
    assert frame.source == "web_stub"
    assert frame.content_area_only is True


def test_web_stub_pipeline_enters_capture_completed(tmp_path):
    pipeline = WebStubPipeline(
        session=make_session(tmp_path, app_id="web_dashboard", run_id="web_run"),
        automation_adapter=StubWebAutomationAdapter(),
    )

    result = pipeline.run(make_web_config())

    assert result.status == RunStatus.CAPTURE_COMPLETED
    assert result.valid_total == 3


def test_web_stub_pipeline_saves_low_bucket_images(tmp_path):
    pipeline = WebStubPipeline(
        session=make_session(tmp_path, app_id="web_dashboard", run_id="web_run"),
        automation_adapter=StubWebAutomationAdapter(),
    )

    result = pipeline.run(make_web_config())

    assert result.low_count == 3
    assert result.high_count == 0


def test_pc_app_pipeline_writes_core_run_files_and_no_upload_manifest(tmp_path):
    pipeline = PcAppStubPipeline(
        session=make_session(tmp_path),
        automation_adapter=StubPcAppAutomationAdapter(),
    )

    result = pipeline.run(make_pc_app_config())

    assert result.summary_path.is_file()
    assert (result.run_dir / "meta.jsonl").is_file()
    assert (result.run_dir / "run.log").is_file()
    assert not (result.run_dir / "upload_manifest.json").exists()
    assert result.status != RunStatus.COMPLETED


def test_web_pipeline_writes_core_run_files_and_no_upload_manifest(tmp_path):
    pipeline = WebStubPipeline(
        session=make_session(tmp_path, app_id="web_dashboard", run_id="web_run"),
        automation_adapter=StubWebAutomationAdapter(),
    )

    result = pipeline.run(make_web_config())

    assert result.summary_path.is_file()
    assert (result.run_dir / "meta.jsonl").is_file()
    assert (result.run_dir / "run.log").is_file()
    assert not (result.run_dir / "upload_manifest.json").exists()
    assert result.status != RunStatus.COMPLETED


def test_pc_app_web_modules_do_not_import_real_execution_libraries():
    source_root = Path(__file__).resolve().parents[2] / "src" / "ai_screenshot_platform"
    files = [
        source_root / "workers" / "pc_app" / "contracts.py",
        source_root / "workers" / "pc_app" / "stub_adapters.py",
        source_root / "workers" / "pc_app" / "pipeline.py",
        source_root / "workers" / "web" / "contracts.py",
        source_root / "workers" / "web" / "stub_adapters.py",
        source_root / "workers" / "web" / "pipeline.py",
    ]
    forbidden_imports = [
        "import pywinauto",
        "from pywinauto",
        "import playwright",
        "from playwright",
        "import mss",
        "import dxcam",
        "import pyautogui",
        "import keyboard",
        "import mouse",
        "import subprocess",
        "from subprocess",
    ]

    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in files)

    for forbidden in forbidden_imports:
        assert forbidden not in combined_source
