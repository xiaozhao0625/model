from __future__ import annotations

import inspect
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
from ai_screenshot_platform.master.services.app_service import AppService
from ai_screenshot_platform.master.services.run_service import RunService
from ai_screenshot_platform.master.services.worker_service import WorkerService


def make_client(tmp_path: Path) -> TestClient:
    settings = MasterSettings(
        database_url=f"sqlite:///{tmp_path / 'master.db'}",
        redis_url="memory://",
        env="test",
        data_root=tmp_path,
    )
    return TestClient(create_app(settings))


def data(response):
    payload = response.json()
    assert payload["code"] == 0
    return payload["data"]


def test_app_can_be_created_listed_and_fetched(tmp_path):
    client = make_client(tmp_path)

    created = data(
        client.post(
            "/api/apps",
            json={
                "app_id": "demo_app",
                "name": "Demo App",
                "type": "pc_app",
                "platform": "windows",
            },
        )
    )
    listed = data(client.get("/api/apps"))
    fetched = data(client.get("/api/apps/demo_app"))

    assert created["app_id"] == "demo_app"
    assert listed[0]["name"] == "Demo App"
    assert fetched["platform"] == "windows"


def test_run_can_be_created_started_and_summarized(tmp_path):
    client = make_client(tmp_path)
    client.post(
        "/api/apps",
        json={
            "app_id": "demo_app",
            "name": "Demo App",
            "type": "pc_game",
            "platform": "windows",
        },
    )

    created = data(
        client.post(
            "/api/runs",
            json={
                "run_id": "run_001",
                "app_id": "demo_app",
                "target_min": 1000,
                "target_max": 5000,
            },
        )
    )
    started = data(client.post("/api/runs/run_001/start"))
    summary = data(client.get("/api/runs/run_001/summary"))

    assert created["status"] == RunStatus.PENDING.value
    assert started["status"] == RunStatus.RUNNING.value
    assert summary["valid_total"] == 0
    assert summary["status"] == RunStatus.RUNNING.value


def test_worker_can_register_heartbeat_and_list(tmp_path):
    client = make_client(tmp_path)

    registered = data(
        client.post(
            "/api/workers/register",
            json={
                "worker_id": "worker_pc_game_w1",
                "type": "pc_game",
                "capabilities": [
                    "capture_high",
                    "behavior_pack",
                    "obs_capture",
                    "ffmpeg_extract",
                ],
            },
        )
    )
    heartbeat = data(client.post("/api/workers/worker_pc_game_w1/heartbeat"))
    workers = data(client.get("/api/workers"))

    assert registered["worker_id"] == "worker_pc_game_w1"
    assert heartbeat["state"] == "idle"
    assert workers[0]["capabilities"] == [
        "capture_high",
        "behavior_pack",
        "obs_capture",
        "ffmpeg_extract",
    ]


def test_mock_upload_flow_reaches_completed_without_local_file_cleanup(tmp_path):
    client = make_client(tmp_path)
    client.post(
        "/api/apps",
        json={
            "app_id": "demo_app",
            "name": "Demo App",
            "type": "pc_app",
            "platform": "windows",
        },
    )
    client.post("/api/runs", json={"run_id": "run_001", "app_id": "demo_app"})
    client.post("/api/runs/run_001/start")

    manifest = data(client.post("/api/upload-manifest", json={"run_id": "run_001"}))
    confirmed = data(client.post("/api/confirm-upload", json={"run_id": "run_001"}))
    cleaned = data(client.post("/api/cleanup", json={"run_id": "run_001"}))
    finalized = data(client.post("/api/finalize", json={"run_id": "run_001"}))

    assert manifest["status"] == RunStatus.UPLOAD_PENDING.value
    assert confirmed["status"] == RunStatus.UPLOADED_CONFIRMED.value
    assert cleaned["status"] == RunStatus.LOCAL_DELETED.value
    assert finalized["status"] == RunStatus.COMPLETED.value


def test_model_gateway_mock_act_allows_safe_and_blocks_risky_instruction(tmp_path):
    client = make_client(tmp_path)

    safe = data(
        client.post(
            "/api/model/act",
            json={
                "app_id": "demo_app",
                "run_id": "run_001",
                "screenshot_path": "runs/demo/screen.webp",
                "scene_class": "menu",
                "instruction": "wait for menu",
            },
        )
    )
    risky = data(
        client.post(
            "/api/model/act",
            json={
                "app_id": "demo_app",
                "run_id": "run_001",
                "screenshot_path": "runs/demo/screen.webp",
                "scene_class": "shop",
                "instruction": "支付订单",
            },
        )
    )

    assert safe["action_type"] == "no_op"
    assert risky["action_type"] == "request_manual"
    assert "payment" in risky["risk_flags"]


def test_settings_identify_sqlite_and_postgresql_modes(tmp_path):
    sqlite_settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    postgres_settings = MasterSettings(
        database_url="postgresql://user:pass@db.example/platform"
    )

    assert sqlite_settings.database_backend == "sqlite"
    assert postgres_settings.database_backend == "postgresql"


def test_services_do_not_contain_sqlite_calls():
    service_sources = "\n".join(
        inspect.getsource(service)
        for service in [AppService, RunService, WorkerService]
    )

    assert "sqlite3" not in service_sources
    assert "SELECT " not in service_sources
