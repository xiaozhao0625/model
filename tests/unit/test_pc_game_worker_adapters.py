from pathlib import Path

from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.workers.pc_game.contracts import (
    CaptureSourceConfig,
    InputCommand,
)
from ai_screenshot_platform.workers.pc_game.pipeline import PcGameStubPipeline
from ai_screenshot_platform.workers.pc_game.stub_adapters import (
    StubFfmpegExtractAdapter,
    StubGameInputAdapter,
    StubObsCaptureAdapter,
)


def make_session(tmp_path, target_min=3):
    return LocalRunSession(
        RunSessionConfig(
            root_dir=tmp_path,
            app_id="demo_game",
            run_id="pc_game_run",
            target_min=target_min,
        )
    )


def make_config():
    return CaptureSourceConfig(
        source_name="mock-source",
        window_title="Mock Game Window",
        fps=30,
        width=1280,
        height=720,
    )


def test_stub_obs_capture_adapter_start_recording_returns_session(tmp_path):
    adapter = StubObsCaptureAdapter(output_dir=tmp_path)

    session = adapter.start_recording(make_config())

    assert session.session_id
    assert session.source_name == "mock-source"
    assert session.started is True
    assert session.output_path.parent == tmp_path


def test_stub_obs_capture_adapter_stop_recording_ends_session(tmp_path):
    adapter = StubObsCaptureAdapter(output_dir=tmp_path)
    session = adapter.start_recording(make_config())

    stopped = adapter.stop_recording(session)

    assert stopped.started is False
    assert stopped.output_path == session.output_path


def test_stub_ffmpeg_extract_adapter_returns_requested_mock_frames(tmp_path):
    obs = StubObsCaptureAdapter(output_dir=tmp_path)
    recording = obs.start_recording(make_config())

    frames = StubFfmpegExtractAdapter().extract_frames(
        recording,
        bucket=Bucket.HIGH,
        max_frames=3,
    )

    assert len(frames) == 3
    assert all(frame.bucket == Bucket.HIGH for frame in frames)
    assert all(frame.image_bytes for frame in frames)


def test_stub_game_input_adapter_never_executes_real_input():
    command = InputCommand(
        command_id="cmd-1",
        command_type="move",
        description="mock move",
        duration_ms=100,
        params={"direction": "forward"},
    )

    result = StubGameInputAdapter().execute(command)

    assert result.command_id == "cmd-1"
    assert result.executed is False
    assert result.skipped is True
    assert "stub" in result.reason


def test_pc_game_stub_pipeline_enters_capture_completed(tmp_path):
    session = make_session(tmp_path, target_min=3)
    pipeline = PcGameStubPipeline(
        session=session,
        obs_adapter=StubObsCaptureAdapter(output_dir=tmp_path),
        ffmpeg_adapter=StubFfmpegExtractAdapter(),
        input_adapter=StubGameInputAdapter(),
    )

    result = pipeline.run(make_config(), max_frames=3)

    assert result.status == RunStatus.CAPTURE_COMPLETED
    assert result.valid_total == 3


def test_pc_game_stub_pipeline_saves_high_bucket_images(tmp_path):
    session = make_session(tmp_path, target_min=3)
    pipeline = PcGameStubPipeline(
        session=session,
        obs_adapter=StubObsCaptureAdapter(output_dir=tmp_path),
        ffmpeg_adapter=StubFfmpegExtractAdapter(),
        input_adapter=StubGameInputAdapter(),
    )

    result = pipeline.run(make_config(), max_frames=3)

    assert result.high_count == 3
    assert result.low_count == 0


def test_pc_game_stub_pipeline_writes_core_run_files(tmp_path):
    session = make_session(tmp_path, target_min=3)
    pipeline = PcGameStubPipeline(
        session=session,
        obs_adapter=StubObsCaptureAdapter(output_dir=tmp_path),
        ffmpeg_adapter=StubFfmpegExtractAdapter(),
        input_adapter=StubGameInputAdapter(),
    )

    result = pipeline.run(make_config(), max_frames=3)

    assert result.summary_path.is_file()
    assert (result.run_dir / "meta.jsonl").is_file()
    assert (result.run_dir / "run.log").is_file()


def test_pc_game_stub_pipeline_does_not_generate_upload_manifest(tmp_path):
    session = make_session(tmp_path, target_min=3)
    pipeline = PcGameStubPipeline(
        session=session,
        obs_adapter=StubObsCaptureAdapter(output_dir=tmp_path),
        ffmpeg_adapter=StubFfmpegExtractAdapter(),
        input_adapter=StubGameInputAdapter(),
    )

    result = pipeline.run(make_config(), max_frames=3)

    assert not (result.run_dir / "upload_manifest.json").exists()


def test_pc_game_stub_pipeline_final_status_is_not_completed(tmp_path):
    session = make_session(tmp_path, target_min=3)
    pipeline = PcGameStubPipeline(
        session=session,
        obs_adapter=StubObsCaptureAdapter(output_dir=tmp_path),
        ffmpeg_adapter=StubFfmpegExtractAdapter(),
        input_adapter=StubGameInputAdapter(),
    )

    result = pipeline.run(make_config(), max_frames=3)

    assert result.status != RunStatus.COMPLETED


def test_pc_game_worker_modules_do_not_import_real_execution_libraries():
    source_root = Path(__file__).resolve().parents[2] / "src" / "ai_screenshot_platform"
    files = [
        source_root / "workers" / "pc_game" / "contracts.py",
        source_root / "workers" / "pc_game" / "stub_adapters.py",
        source_root / "workers" / "pc_game" / "pipeline.py",
    ]
    forbidden_imports = [
        "import obsws",
        "import ffmpeg",
        "import pydirectinput",
        "import keyboard",
        "import mouse",
        "import pyautogui",
        "import subprocess",
    ]

    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in files)

    for forbidden in forbidden_imports:
        assert forbidden not in combined_source
