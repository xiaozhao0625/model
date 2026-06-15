from __future__ import annotations

import inspect
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

from fastapi.testclient import TestClient

from apps.master_api.main import app as importable_app
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.api.app import create_app, _redis_endpoint
from ai_screenshot_platform.master.core.config import MasterSettings
from ai_screenshot_platform.master.services.artifact_inspector_service import ArtifactInspectorService
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


def test_artifact_inspector_parses_json_before_powershell_noise():
    payload = '{"status":"ok","has_summary_json":true}\n#< CLIXML\n<Objs></Objs>'

    parsed = ArtifactInspectorService._parse_remote_json_output(payload)

    assert parsed == {"status": "ok", "has_summary_json": True}


def test_default_database_url_uses_runs_master_path():
    settings = MasterSettings()

    assert settings.database_url == "sqlite:///runs/master/master.db"
    assert settings.sqlite_path.name == "master.db"
    assert settings.sqlite_path.parent.name == "master"


def test_database_url_can_be_overridden_by_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")

    settings = MasterSettings.from_env()

    assert settings.database_url == "postgresql://user:pass@host:5432/db"
    assert settings.database_backend == "postgresql"


def test_dotenv_loader_accepts_utf8_bom(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / ".env").write_text(
        "\ufeffDATABASE_URL=postgresql://user:pass@127.0.0.1:5432/app\n",
        encoding="utf-8",
    )

    settings = MasterSettings.from_env()

    assert settings.database_backend == "postgresql"


def test_default_cors_origins_include_vite_lan_port():
    settings = MasterSettings()

    assert "http://127.0.0.1:5173" in settings.cors_origins
    assert "http://localhost:5173" in settings.cors_origins
    assert "http://192.168.1.18:5173" in settings.cors_origins


def test_importable_app_does_not_create_root_master_db():
    root_db = Path("master.db")
    if root_db.exists():
        root_db.unlink()

    __import__("apps.master_api.main")

    assert not root_db.exists()


def test_gitignore_ignores_db_files_and_runs_directory():
    gitignore = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert "*.db" in gitignore
    assert "/runs/" in gitignore


def test_fastapi_app_importable_from_apps_master_api_main():
    assert importable_app.title == "AI Screenshot Platform Master API"


def test_health_and_openapi_are_available(tmp_path):
    with make_client(tmp_path) as client:
        health = client.get("/health")
        openapi = client.get("/openapi.json")

        assert health.status_code == 200
        assert health.json()["data"]["status"] == "ok"
        assert openapi.status_code == 200


def test_redis_endpoint_uses_configured_port():
    assert _redis_endpoint("redis://127.0.0.1:6479/0") == ("127.0.0.1", 6479)
    assert _redis_endpoint("redis://redis.local/0") == ("redis.local", 6379)
    assert _redis_endpoint("memory://") is None


def test_testclient_startup_creates_configured_sqlite_database(tmp_path):
    db_path = tmp_path / "custom" / "master.db"
    settings = MasterSettings(
        database_url=f"sqlite:///{db_path}",
        redis_url="memory://",
        env="test",
        data_root=tmp_path,
    )
    app = create_app(settings)

    assert not db_path.exists()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert db_path.exists()


def test_openapi_contains_stable_master_routes(tmp_path):
    with make_client(tmp_path) as client:
        paths = client.get("/openapi.json").json()["paths"]

        assert "/api/apps" in paths
        assert "/api/runs" in paths
        assert "/api/tasks" in paths
        assert "/api/workers/register" in paths
        assert "/api/runs/{run_id}/upload-manifest" in paths
        assert "/api/runs/{run_id}/confirm-upload" in paths
        assert "/api/runs/{run_id}/cleanup" in paths
        assert "/api/runs/{run_id}/finalize" in paths
        assert "/api/model/deployment-matrix" in paths


def test_model_deployment_matrix_includes_showui_provider_plan(tmp_path):
    with make_client(tmp_path) as client:
        matrix = data(client.get("/api/model/deployment-matrix"))

        showui = next(provider for provider in matrix["providers"] if provider["provider"] == "showui")
        assert showui["target_node"] == "M0"
        assert showui["health_status"] in {"missing_weights", "inference_ok"}
        assert showui["enabled"] is False
        assert showui["online_inference_enabled"] is False


def test_app_can_be_created_listed_and_fetched(tmp_path):
    with make_client(tmp_path) as client:
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
        assert created["backend_source"] == "database"
        assert created["created_at"]
        assert listed[0]["name"] == "Demo App"
        assert fetched["platform"] == "windows"


def test_app_create_persists_across_master_restart(tmp_path):
    with make_client(tmp_path) as client:
        created = data(
            client.post(
                "/api/apps",
                json={
                    "app_id": "persistent_app",
                    "name": "Persistent App",
                    "type": "web",
                    "platform": "browser",
                },
            )
        )

    with make_client(tmp_path) as restarted_client:
        listed = data(restarted_client.get("/api/apps"))
        fetched = data(restarted_client.get("/api/apps/persistent_app"))

    assert created["app_id"] == "persistent_app"
    assert fetched["app_id"] == "persistent_app"
    assert fetched["backend_source"] == "database"
    assert any(app["app_id"] == "persistent_app" for app in listed)


def test_run_can_be_created_started_and_summarized(tmp_path):
    with make_client(tmp_path) as client:
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
    with make_client(tmp_path) as client:
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


def test_worker_claim_and_report_preserve_run_worker_identity(tmp_path):
    with make_client(tmp_path) as client:
        client.post(
            "/api/apps",
            json={
                "app_id": "demo_app",
                "name": "Demo App",
                "type": "pc_game",
                "platform": "windows",
            },
        )
        client.post("/api/runs", json={"run_id": "run_worker_identity", "app_id": "demo_app"})
        client.post(
            "/api/workers/register",
            json={
                "worker_id": "worker_pc_game_w1",
                "type": "pc_game",
                "capabilities": ["capture_high"],
            },
        )

        claim = data(client.post("/api/workers/worker_pc_game_w1/claim"))
        claimed_run = data(client.get("/api/runs/run_worker_identity"))
        report = data(
            client.post(
                "/api/workers/worker_pc_game_w1/runs/run_worker_identity/report",
                json={
                    "app_id": "demo_app",
                    "run_id": "run_worker_identity",
                    "status": "capture_completed",
                    "valid_total": 10,
                    "fixed_count": 0,
                    "low_count": 0,
                    "high_count": 10,
                    "rejected_count": 0,
                    "run_dir": "runs/run_worker_identity",
                    "summary_path": "runs/run_worker_identity/summary.json",
                },
            )
        )
        final_run = data(client.get("/api/runs/run_worker_identity"))

        assert claim["status"] == "claimed"
        assert claimed_run["worker_id"] == "worker_pc_game_w1"
        assert report["run"]["worker_id"] == "worker_pc_game_w1"
        assert final_run["worker_id"] == "worker_pc_game_w1"
        assert final_run["assigned_worker_id"] == "worker_pc_game_w1"
        assert final_run["executed_by"] == "worker_pc_game_w1"


def test_capture_completed_run_can_be_marked_failed_low_yield_with_audit(tmp_path):
    with make_client(tmp_path) as client:
        client.post(
            "/api/apps",
            json={
                "app_id": "demo_app",
                "name": "Demo App",
                "type": "pc_game",
                "platform": "windows",
            },
        )
        client.post("/api/runs", json={"run_id": "run_low_yield_action", "app_id": "demo_app"})
        client.post(
            "/api/workers/register",
            json={
                "worker_id": "worker_pc_game_w1",
                "type": "pc_game",
                "capabilities": ["capture_high"],
            },
        )
        client.post("/api/workers/worker_pc_game_w1/claim")
        client.post(
            "/api/workers/worker_pc_game_w1/runs/run_low_yield_action/report",
            json={
                "app_id": "demo_app",
                "run_id": "run_low_yield_action",
                "status": "capture_completed",
                "valid_total": 3,
                "fixed_count": 0,
                "low_count": 0,
                "high_count": 3,
                "rejected_count": 0,
                "run_dir": "runs/run_low_yield_action",
                "summary_path": "runs/run_low_yield_action/summary.json",
            },
        )

        updated = data(
            client.post(
                "/api/runs/run_low_yield_action/mark-failed-low-yield",
                json={"operator_action": "mark_failed_low_yield"},
            )
        )
        listed = data(client.get("/api/runs"))["items"]
        fetched = data(client.get("/api/runs/run_low_yield_action"))
        summary = data(client.get("/api/runs/run_low_yield_action/summary"))
        events = data(client.get("/api/runs/run_low_yield_action/status-events"))

        assert updated["status"] == RunStatus.FAILED_LOW_YIELD.value
        assert next(run for run in listed if run["run_id"] == "run_low_yield_action")["status"] == RunStatus.FAILED_LOW_YIELD.value
        assert fetched["status"] == RunStatus.FAILED_LOW_YIELD.value
        assert summary["status"] == RunStatus.FAILED_LOW_YIELD.value
        assert events[-1]["previous_status"] == RunStatus.CAPTURE_COMPLETED.value
        assert events[-1]["new_status"] == RunStatus.FAILED_LOW_YIELD.value
        assert events[-1]["operator_action"] == "mark_failed_low_yield"


def test_run_list_supports_filters_sort_and_pagination(tmp_path):
    with make_client(tmp_path) as client:
        client.post(
            "/api/apps",
            json={"app_id": "demo_app", "name": "Demo App", "type": "pc_app", "platform": "windows"},
        )
        client.post("/api/runs", json={"run_id": "p14_4_batch2_w2_web_content_01_20260615_175326_run", "app_id": "demo_app"})
        client.post("/api/runs", json={"run_id": "p14_4_batch3_w1_safe_window_01_20260615_182924_run", "app_id": "demo_app"})
        client.post(
            "/api/workers/register",
            json={"worker_id": "worker_pc_app_web_w2", "type": "web", "capabilities": ["capture_low"]},
        )
        client.post(
            "/api/workers/worker_pc_app_web_w2/runs/p14_4_batch2_w2_web_content_01_20260615_175326_run/report",
            json={
                "app_id": "demo_app",
                "run_id": "p14_4_batch2_w2_web_content_01_20260615_175326_run",
                "status": "capture_completed",
                "valid_total": 30,
                "fixed_count": 0,
                "low_count": 30,
                "high_count": 0,
                "rejected_count": 0,
                "run_dir": "runs/p14_4_batch2_w2_web_content_01_20260615_175326_run",
                "summary_path": "runs/p14_4_batch2_w2_web_content_01_20260615_175326_run/summary.json",
            },
        )

        listed = data(client.get("/api/runs?sort=created_at_desc&limit=1"))
        filtered = data(client.get("/api/runs?worker_id=worker_pc_app_web_w2&status=capture_completed&batch=p14_4_batch2"))
        searched = data(client.get("/api/tasks?q=web_content&limit=5"))

        assert listed["total"] == 2
        assert listed["items"][0]["run_id"] == "p14_4_batch3_w1_safe_window_01_20260615_182924_run"
        assert filtered["total"] == 1
        assert filtered["items"][0]["worker_id"] == "worker_pc_app_web_w2"
        assert searched["items"][0]["batch"] == "p14_4_batch2"


def test_model_deployment_matrix_is_plan_only_and_distributed(tmp_path):
    with make_client(tmp_path) as client:
        matrix = data(client.get("/api/model/deployment-matrix"))

        assert matrix["status"] == "planned_only"
        assert matrix["online_inference_enabled"] is False
        assert matrix["model_downloaded"] in {False, True}
        assert matrix["ocr_installed"] is False
        assert [node["role"] for node in matrix["nodes"]] == ["M0", "W1", "W2", "W3"]
        assert next(node for node in matrix["nodes"] if node["role"] == "M0")["models_dir"] == r"E:\work\models"
        assert next(node for node in matrix["nodes"] if node["role"] == "W2")["ocr_dir"] == r"D:\work\ocr"


def test_mock_upload_flow_reaches_completed_without_local_file_cleanup(tmp_path):
    with make_client(tmp_path) as client:
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


def test_run_scoped_upload_routes_reuse_upload_flow(tmp_path):
    with make_client(tmp_path) as client:
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

        manifest = data(client.post("/api/runs/run_001/upload-manifest"))
        confirmed = data(client.post("/api/runs/run_001/confirm-upload"))
        cleaned = data(client.post("/api/runs/run_001/cleanup"))
        finalized = data(client.post("/api/runs/run_001/finalize"))

        assert manifest["status"] == RunStatus.UPLOAD_PENDING.value
        assert confirmed["status"] == RunStatus.UPLOADED_CONFIRMED.value
        assert cleaned["status"] == RunStatus.LOCAL_DELETED.value
        assert finalized["status"] == RunStatus.COMPLETED.value


def test_model_gateway_mock_act_allows_safe_and_blocks_risky_instruction(tmp_path):
    with make_client(tmp_path) as client:
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
                    "instruction": "payment checkout",
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
