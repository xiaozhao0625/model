from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.worker.contracts import (
    WorkerCapability,
    WorkerProfile,
    WorkerState,
    WorkerTask,
    WorkerType,
)
from ai_screenshot_platform.common.worker.mock_worker import MockWorkerAgent
from ai_screenshot_platform.common.worker.registry import WorkerRegistry


def make_profile(
    worker_id="worker-1",
    worker_type=WorkerType.MOCK,
    capabilities=None,
    state=WorkerState.IDLE,
    enabled=True,
):
    return WorkerProfile(
        worker_id=worker_id,
        machine_name="test-machine",
        worker_type=worker_type,
        gpu_name=None,
        capabilities=set(capabilities or {WorkerCapability.CAPTURE_LOW}),
        state=state,
        current_run_id=None,
        enabled=enabled,
    )


def test_worker_profile_can_express_mock_worker():
    profile = make_profile()

    assert profile.worker_type == WorkerType.MOCK
    assert WorkerCapability.CAPTURE_LOW in profile.capabilities
    assert profile.state == WorkerState.IDLE


def test_worker_profile_can_express_pc_game_worker_high_capture_stack():
    profile = make_profile(
        worker_id="pc-game-1",
        worker_type=WorkerType.PC_GAME,
        capabilities={
            WorkerCapability.CAPTURE_HIGH,
            WorkerCapability.BEHAVIOR_PACK,
            WorkerCapability.OBS_CAPTURE,
            WorkerCapability.FFMPEG_EXTRACT,
        },
    )

    assert WorkerCapability.CAPTURE_HIGH in profile.capabilities
    assert WorkerCapability.BEHAVIOR_PACK in profile.capabilities
    assert WorkerCapability.OBS_CAPTURE in profile.capabilities
    assert WorkerCapability.FFMPEG_EXTRACT in profile.capabilities


def test_worker_profile_can_express_web_worker():
    profile = make_profile(
        worker_id="web-1",
        worker_type=WorkerType.WEB,
        capabilities={WorkerCapability.CAPTURE_LOW, WorkerCapability.PLAYWRIGHT},
    )

    assert WorkerCapability.CAPTURE_LOW in profile.capabilities
    assert WorkerCapability.PLAYWRIGHT in profile.capabilities


def test_worker_profile_can_express_android_worker():
    profile = make_profile(
        worker_id="android-1",
        worker_type=WorkerType.ANDROID,
        capabilities={WorkerCapability.CAPTURE_LOW, WorkerCapability.ADB},
    )

    assert WorkerCapability.CAPTURE_LOW in profile.capabilities
    assert WorkerCapability.ADB in profile.capabilities


def test_worker_registry_can_register_and_get_worker():
    registry = WorkerRegistry()
    profile = make_profile()

    registry.register(profile)

    assert registry.get("worker-1") == profile


def test_worker_registry_can_filter_by_capabilities():
    registry = WorkerRegistry()
    low_profile = make_profile(
        worker_id="low-1",
        capabilities={WorkerCapability.CAPTURE_LOW},
    )
    high_profile = make_profile(
        worker_id="high-1",
        capabilities={
            WorkerCapability.CAPTURE_HIGH,
            WorkerCapability.BEHAVIOR_PACK,
            WorkerCapability.OBS_CAPTURE,
            WorkerCapability.FFMPEG_EXTRACT,
        },
    )
    registry.register(low_profile)
    registry.register(high_profile)

    matched = registry.find_by_capabilities(
        {
            WorkerCapability.CAPTURE_HIGH,
            WorkerCapability.BEHAVIOR_PACK,
            WorkerCapability.OBS_CAPTURE,
            WorkerCapability.FFMPEG_EXTRACT,
        }
    )

    assert matched == [high_profile]


def test_disabled_or_non_idle_worker_is_not_available():
    registry = WorkerRegistry()
    idle = make_profile(worker_id="idle")
    disabled = make_profile(worker_id="disabled", enabled=False)
    running = make_profile(worker_id="running", state=WorkerState.RUNNING)
    registry.register(idle)
    registry.register(disabled)
    registry.register(running)

    assert registry.list_available() == [idle]


def test_mock_worker_agent_can_execute_task(tmp_path):
    profile = make_profile()
    agent = MockWorkerAgent(profile)
    task = WorkerTask(
        app_id="demo_app",
        run_id="run_001",
        app_type="desktop",
        platform="windows",
        target_min=3,
        target_max=5000,
        bucket="low",
        root_dir=tmp_path,
    )

    result = agent.execute(task)

    assert result.status == RunStatus.CAPTURE_COMPLETED
    assert result.valid_total == 3
    assert result.low_count == 3
    assert result.high_count == 0
    assert result.error is None


def test_mock_worker_agent_writes_summary_and_meta_jsonl(tmp_path):
    profile = make_profile()
    agent = MockWorkerAgent(profile)
    task = WorkerTask(
        app_id="demo_app",
        run_id="run_001",
        app_type="desktop",
        platform="windows",
        target_min=3,
        target_max=5000,
        bucket="low",
        root_dir=tmp_path,
    )

    result = agent.execute(task)

    assert Path(result.summary_path).is_file()
    assert (Path(result.run_dir) / "meta.jsonl").is_file()


def test_mock_worker_agent_does_not_generate_upload_manifest(tmp_path):
    profile = make_profile()
    agent = MockWorkerAgent(profile)
    task = WorkerTask(
        app_id="demo_app",
        run_id="run_001",
        app_type="desktop",
        platform="windows",
        target_min=3,
        target_max=5000,
        bucket="low",
        root_dir=tmp_path,
    )

    result = agent.execute(task)

    assert not (Path(result.run_dir) / "upload_manifest.json").exists()


def test_mock_worker_agent_does_not_enter_completed(tmp_path):
    profile = make_profile()
    agent = MockWorkerAgent(profile)
    task = WorkerTask(
        app_id="demo_app",
        run_id="run_001",
        app_type="desktop",
        platform="windows",
        target_min=3,
        target_max=5000,
        bucket="low",
        root_dir=tmp_path,
    )

    result = agent.execute(task)

    assert result.status != RunStatus.COMPLETED
