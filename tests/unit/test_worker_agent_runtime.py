from __future__ import annotations

import json
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

from fastapi.testclient import TestClient

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.worker.contracts import WorkerTask
from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings
from ai_screenshot_platform.worker_agent.config import (
    WorkerAgentConfigLoader,
)
from ai_screenshot_platform.worker_agent.executors import ExecutorResolver
from ai_screenshot_platform.worker_agent.master_client import MasterApiClient
from ai_screenshot_platform.worker_agent.runtime import WorkerRuntime


def make_client(tmp_path: Path) -> TestClient:
    settings = MasterSettings(
        database_url=f"sqlite:///{tmp_path / 'master.db'}",
        redis_url="memory://",
        env="test",
        data_root=tmp_path / "master",
    )
    return TestClient(create_app(settings))


def unwrap(response):
    payload = response.json()
    assert payload["code"] == 0
    return payload["data"]


def test_worker_agent_config_loader_reads_example():
    configs = WorkerAgentConfigLoader.load_many(
        "configs/workers/worker_agent.single_node_dev.example.json"
    )

    assert {config.execution_mode for config in configs} >= {"mock", "web_stub"}
    assert configs[0].worker_id
    assert configs[0].data_root


def test_master_client_register_heartbeat_and_no_task_claim(tmp_path):
    with make_client(tmp_path) as api:
        client = MasterApiClient("testserver", test_client=api)

        registered = client.register_worker(
            worker_id="worker_mock_1",
            worker_type="mock",
            machine_name="local-dev",
            capabilities=["capture_low"],
        )
        heartbeat = client.send_heartbeat("worker_mock_1")
        claim = client.claim_task("worker_mock_1")

        assert registered["state"] == "idle"
        assert heartbeat["worker_id"] == "worker_mock_1"
        assert claim["status"] == "no_task"
        assert claim["task"] is None


def test_worker_runtime_no_task_exits_safely(tmp_path):
    with make_client(tmp_path) as api:
        runtime = WorkerRuntime(
            config=WorkerAgentConfigLoader.from_dict(
                {
                    "worker_id": "worker_mock_1",
                    "worker_type": "mock",
                    "machine_name": "local-dev",
                    "capabilities": ["capture_low"],
                    "master_url": "testserver",
                    "data_root": str(tmp_path / "worker"),
                    "heartbeat_interval_sec": 1,
                    "execution_mode": "mock",
                }
            ),
            client=MasterApiClient("testserver", test_client=api),
        )

        result = runtime.start_once()

        assert result["claim_status"] == "no_task"
        assert result["execution_status"] is None


def test_executor_resolver_runs_mock_pc_game_and_web_stub(tmp_path):
    resolver = ExecutorResolver()

    for mode, bucket in [
        ("mock", "low"),
        ("pc_game_stub", "high"),
        ("web_stub", "low"),
    ]:
        task = WorkerTask(
            app_id=f"app_{mode}",
            run_id=f"run_{mode}",
            app_type="pc_game" if mode == "pc_game_stub" else "web",
            platform="windows",
            target_min=3,
            target_max=5000,
            bucket=bucket,
            root_dir=tmp_path / mode,
        )

        result = resolver.execute(mode, task)

        assert result.status == RunStatus.CAPTURE_COMPLETED
        assert result.valid_total == 3
        assert result.summary_path.exists()
        assert not (result.run_dir / "upload_manifest.json").exists()


def test_worker_runtime_reports_mock_result_and_does_not_complete(tmp_path):
    with make_client(tmp_path) as api:
        api.post(
            "/api/apps",
            json={
                "app_id": "demo_app",
                "name": "Demo App",
                "type": "pc_app",
                "platform": "windows",
            },
        )
        api.post(
            "/api/runs",
            json={
                "run_id": "run_001",
                "app_id": "demo_app",
                "target_min": 3,
                "target_max": 5000,
            },
        )
        runtime = WorkerRuntime(
            config=WorkerAgentConfigLoader.from_dict(
                {
                    "worker_id": "worker_mock_1",
                    "worker_type": "mock",
                    "machine_name": "local-dev",
                    "capabilities": ["capture_low"],
                    "master_url": "testserver",
                    "data_root": str(tmp_path / "worker"),
                    "heartbeat_interval_sec": 1,
                    "execution_mode": "mock",
                }
            ),
            client=MasterApiClient("testserver", test_client=api),
        )

        result = runtime.start_once()
        final_run = unwrap(api.get("/api/runs/run_001"))

        assert result["claim_status"] == "claimed"
        assert result["execution_status"] == RunStatus.CAPTURE_COMPLETED.value
        assert final_run["status"] == RunStatus.CAPTURE_COMPLETED.value
        assert final_run["valid_total"] == 3
        assert final_run["status"] != RunStatus.COMPLETED.value


def test_worker_config_example_is_json_object():
    payload = json.loads(
        Path("configs/workers/worker_agent.single_node_dev.example.json").read_text(
            encoding="utf-8"
        )
    )

    assert isinstance(payload["workers"], list)
    assert payload["workers"]
