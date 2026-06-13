from __future__ import annotations

import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

from fastapi.testclient import TestClient

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings
from ai_screenshot_platform.worker_agent.config import WorkerAgentConfigLoader
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


def test_master_worker_full_mock_flow_reaches_capture_completed(tmp_path):
    with make_client(tmp_path) as api:
        unwrap(
            api.post(
                "/api/apps",
                json={
                    "app_id": "demo_app",
                    "name": "Demo App",
                    "type": "pc_app",
                    "platform": "windows",
                },
            )
        )
        unwrap(
            api.post(
                "/api/runs",
                json={
                    "run_id": "demo_run",
                    "app_id": "demo_app",
                    "target_min": 3,
                    "target_max": 5000,
                },
            )
        )
        runtime = WorkerRuntime(
            config=WorkerAgentConfigLoader.from_dict(
                {
                    "worker_id": "worker_mock_1",
                    "worker_type": "mock",
                    "machine_name": "single-node",
                    "capabilities": ["capture_low"],
                    "master_url": "testserver",
                    "data_root": str(tmp_path / "worker"),
                    "heartbeat_interval_sec": 1,
                    "execution_mode": "mock",
                }
            ),
            client=MasterApiClient("testserver", test_client=api),
        )

        runtime_result = runtime.start_once()
        final_run = unwrap(api.get("/api/runs/demo_run"))
        workers = unwrap(api.get("/api/workers"))

        assert runtime_result["claim_status"] == "claimed"
        assert runtime_result["execution_status"] == RunStatus.CAPTURE_COMPLETED.value
        assert final_run["status"] == RunStatus.CAPTURE_COMPLETED.value
        assert final_run["valid_total"] == 3
        assert final_run["low_count"] == 3
        assert workers[0]["state"] == "idle"
        assert workers[0]["current_run_id"] is None
        assert not (Path(runtime_result["run_dir"]) / "upload_manifest.json").exists()


def test_master_openapi_contains_worker_claim_and_report_routes(tmp_path):
    with make_client(tmp_path) as api:
        paths = api.get("/openapi.json").json()["paths"]

        assert "/api/workers/{worker_id}/claim" in paths
        assert "/api/workers/{worker_id}/runs/{run_id}/report" in paths
        assert "/api/workers/register" in paths
        assert "/api/workers/{worker_id}/heartbeat" in paths


def test_unregistered_worker_cannot_claim(tmp_path):
    with make_client(tmp_path) as api:
        response = api.post("/api/workers/missing_worker/claim")

        assert response.status_code == 404


def test_report_rejects_completed_status_from_worker(tmp_path):
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
                "run_id": "demo_run",
                "app_id": "demo_app",
                "target_min": 3,
                "target_max": 5000,
            },
        )
        api.post(
            "/api/workers/register",
            json={
                "worker_id": "worker_mock_1",
                "type": "mock",
                "capabilities": ["capture_low"],
            },
        )
        unwrap(api.post("/api/workers/worker_mock_1/claim"))

        response = api.post(
            "/api/workers/worker_mock_1/runs/demo_run/report",
            json={
                "app_id": "demo_app",
                "run_id": "demo_run",
                "status": "completed",
                "valid_total": 3,
                "fixed_count": 0,
                "low_count": 3,
                "high_count": 0,
                "rejected_count": 0,
                "run_dir": str(tmp_path),
                "summary_path": str(tmp_path / "summary.json"),
            },
        )

        assert response.status_code == 400
