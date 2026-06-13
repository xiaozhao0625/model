from pathlib import Path

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.workers.android.contracts import (
    AndroidDeviceCommand,
    AndroidTargetConfig,
)
from ai_screenshot_platform.workers.android.pipeline import AndroidStubPipeline
from ai_screenshot_platform.workers.android.reuse_mapping import AndroidReuseMapping
from ai_screenshot_platform.workers.android.stub_adapters import (
    StubAndroidDeviceAdapter,
    StubAndroidQualityAdapter,
    StubAndroidUiObserverAdapter,
)


def make_session(tmp_path, target_min=3):
    return LocalRunSession(
        RunSessionConfig(
            root_dir=tmp_path,
            app_id="android_demo",
            run_id="android_run",
            target_min=target_min,
        )
    )


def make_config():
    return AndroidTargetConfig(
        app_id="android_demo",
        package_name="com.example.demo",
        activity_name=".MainActivity",
        device_id="mock-device",
    )


def test_android_reuse_mapping_contains_key_app_screenshot_agent_modules():
    mapping = AndroidReuseMapping.default()

    assert mapping.target_for("ADB 控制") == "AndroidDeviceAdapter"
    assert mapping.target_for("OCR Adapter") == "future common/ocr"
    assert mapping.target_for("UIAutomator 解析") == "AndroidUiObserverAdapter"
    assert mapping.target_for("QualityChecker") == "AndroidQualityAdapter"
    assert mapping.target_for("DuplicateChecker") == "common quality/dedup"
    assert mapping.target_for("StateManager") == "LocalRunSession / meta.jsonl recovery"
    assert mapping.target_for("ScreenshotManager") == "BucketedScreenshotStore"


def test_stub_android_device_adapter_connect_does_not_execute_real_adb():
    result = StubAndroidDeviceAdapter().connect(make_config())

    assert result.command_id == "connect:mock-device"
    assert result.executed is False
    assert result.skipped is True
    assert "stub" in result.reason


def test_stub_android_device_adapter_capture_frame_returns_mock_frame():
    frame = StubAndroidDeviceAdapter().capture_frame(make_config())

    assert frame.frame_id
    assert frame.image_bytes
    assert frame.bucket == Bucket.LOW
    assert frame.source == "android_stub"


def test_stub_android_ui_observer_returns_mock_observation():
    observation = StubAndroidUiObserverAdapter().observe(make_config())

    assert observation.app_id == "android_demo"
    assert observation.package_name == "com.example.demo"
    assert observation.source == "android_ui_stub"
    assert observation.elements


def test_stub_android_quality_adapter_returns_valid_true():
    frame = StubAndroidDeviceAdapter().capture_frame(make_config())

    result = StubAndroidQualityAdapter().check(frame)

    assert result.valid is True
    assert result.reason == "stub_quality_valid"


def test_android_stub_pipeline_enters_capture_completed(tmp_path):
    pipeline = AndroidStubPipeline(
        session=make_session(tmp_path),
        device_adapter=StubAndroidDeviceAdapter(),
        ui_observer=StubAndroidUiObserverAdapter(),
        quality_adapter=StubAndroidQualityAdapter(),
    )

    result = pipeline.run(make_config())

    assert result.status == RunStatus.CAPTURE_COMPLETED
    assert result.valid_total == 3


def test_android_stub_pipeline_saves_low_bucket_images(tmp_path):
    pipeline = AndroidStubPipeline(
        session=make_session(tmp_path),
        device_adapter=StubAndroidDeviceAdapter(),
        ui_observer=StubAndroidUiObserverAdapter(),
        quality_adapter=StubAndroidQualityAdapter(),
    )

    result = pipeline.run(make_config())

    assert result.low_count == 3
    assert result.high_count == 0


def test_android_stub_pipeline_writes_core_files_and_no_upload_manifest(tmp_path):
    pipeline = AndroidStubPipeline(
        session=make_session(tmp_path),
        device_adapter=StubAndroidDeviceAdapter(),
        ui_observer=StubAndroidUiObserverAdapter(),
        quality_adapter=StubAndroidQualityAdapter(),
    )

    result = pipeline.run(make_config())

    assert result.summary_path.is_file()
    assert (result.run_dir / "meta.jsonl").is_file()
    assert (result.run_dir / "run.log").is_file()
    assert not (result.run_dir / "upload_manifest.json").exists()
    assert result.status != RunStatus.COMPLETED


def test_stub_android_execute_command_never_executes_real_device_action():
    command = AndroidDeviceCommand(
        command_id="tap_1",
        command_type="tap",
        description="mock tap",
        params={"x": 10, "y": 20},
    )

    result = StubAndroidDeviceAdapter().execute(command)

    assert result.executed is False
    assert result.skipped is True
    assert "stub" in result.reason


def test_android_modules_do_not_import_real_device_or_ocr_libraries():
    source_root = Path(__file__).resolve().parents[2] / "src" / "ai_screenshot_platform"
    files = [
        source_root / "workers" / "android" / "contracts.py",
        source_root / "workers" / "android" / "reuse_mapping.py",
        source_root / "workers" / "android" / "stub_adapters.py",
        source_root / "workers" / "android" / "pipeline.py",
    ]
    forbidden_imports = [
        "import adb",
        "from adb",
        "import appium",
        "from appium",
        "import airtest",
        "from airtest",
        "import paddleocr",
        "import easyocr",
        "import subprocess",
        "from subprocess",
    ]

    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in files)

    for forbidden in forbidden_imports:
        assert forbidden not in combined_source
