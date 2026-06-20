from fastapi.testclient import TestClient

from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings


def test_v3_api_create_start_summary(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/v3/health").json()
        assert health["ok"] is True
        data = health["data"]
        assert data["ocr_production_ready"] is False
        assert data["full_auto_capture_ready"] is False
        assert data["readiness_blockers"]
        created = client.post("/api/v3/runs", json={"config": {"save_root": str(tmp_path / "v3")}}).json()["data"]
        started = client.post(f"/api/v3/runs/{created['run_id']}/start").json()["data"]
        summary = client.get(f"/api/v3/runs/{created['run_id']}/summary").json()["data"]
        assert started["status"] == "running"
        assert summary["observe_only"] is True


def test_v3_api_accepts_web_app_type(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v3/runs",
            json={"config": {"save_root": str(tmp_path / "v3"), "app_type": "web"}},
        )
        assert response.status_code == 200
        assert response.json()["data"]["config"]["app_type"] == "web"


def test_v3_api_accepts_pc_app_type_and_twenty_actions(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v3/runs",
            json={
                "config": {
                    "save_root": str(tmp_path / "v3"),
                    "app_type": "pc_app",
                    "max_actions": 20,
                }
            },
        )
        assert response.status_code == 200
        config = response.json()["data"]["config"]
        assert config["app_type"] == "pc_app"
        assert config["max_actions"] == 20


def test_v3_api_ingests_image_into_run(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    image = tmp_path / "start_button.png"
    image.write_bytes(b"not-empty")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/runs",
            json={
                "config": {
                    "save_root": str(tmp_path / "v3"),
                    "target_language": "en",
                    "must_have_text": True,
                }
            },
        ).json()["data"]

        ingested = client.post(
            f"/api/v3/runs/{created['run_id']}/images/ingest",
            json={"image_path": str(image)},
        ).json()["data"]

        assert ingested["path"] == str(image)
        assert ingested["bucket"] == "accepted"


def test_v3_api_get_actions_is_read_only(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/runs",
            json={"config": {"save_root": str(tmp_path / "v3")}},
        ).json()["data"]

        actions = client.get(f"/api/v3/runs/{created['run_id']}/actions").json()["data"]
        summary = client.get(f"/api/v3/runs/{created['run_id']}/summary").json()["data"]

        assert actions == []
        assert summary["counts"]["actions"] == 0


def test_v3_api_post_evaluate_records_non_executed_action(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    image = tmp_path / "start_button.png"
    image.write_bytes(b"not-empty")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/runs",
            json={
                "config": {
                    "save_root": str(tmp_path / "v3"),
                    "target_language": "en",
                    "must_have_text": True,
                    "enable_auto_click": True,
                    "observe_only": False,
                }
            },
        ).json()["data"]
        client.post(f"/api/v3/runs/{created['run_id']}/images/ingest", json={"image_path": str(image)})

        evaluated = client.post(f"/api/v3/runs/{created['run_id']}/actions/evaluate").json()["data"]
        listed = client.get(f"/api/v3/runs/{created['run_id']}/actions").json()["data"]

        assert evaluated[0]["label"] == "Start"
        assert evaluated[0]["result"]["executed"] is False
        assert evaluated[0]["result"]["status"] == "evaluated"
        assert listed[0]["result"]["status"] == "evaluated"


def test_v3_api_post_execute_records_action_without_default_real_click(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    image = tmp_path / "start_button.png"
    image.write_bytes(b"not-empty")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/runs",
            json={
                "config": {
                    "save_root": str(tmp_path / "v3"),
                    "target_language": "en",
                    "must_have_text": True,
                    "enable_auto_click": True,
                    "observe_only": False,
                }
            },
        ).json()["data"]
        client.post(f"/api/v3/runs/{created['run_id']}/images/ingest", json={"image_path": str(image)})

        executed = client.post(f"/api/v3/runs/{created['run_id']}/actions/execute").json()["data"]
        summary = client.get(f"/api/v3/runs/{created['run_id']}/summary").json()["data"]

        assert executed[0]["label"] == "Start"
        assert executed[0]["result"]["executed"] is False
        assert executed[0]["result"]["reason"] == "real_click_disabled_by_default"
        assert summary["counts"]["actions"] == 1


def test_v3_api_records_external_action_audit(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/runs",
            json={"config": {"save_root": str(tmp_path / "v3")}},
        ).json()["data"]
        action = {
            "label": "File",
            "source_candidate_id": "ocr_box:File:1:2:3:4",
            "before_image": "before.png",
            "after_image": "after.png",
            "result": {"executed": True, "status": "menu_opened", "reason": "computer_use_click"},
            "safety_result": {"allowed": True, "reason": "allowed"},
        }

        response = client.post(f"/api/v3/runs/{created['run_id']}/actions/record", json={"action": action})
        listed = client.get(f"/api/v3/runs/{created['run_id']}/actions").json()["data"]
        summary = client.get(f"/api/v3/runs/{created['run_id']}/summary").json()["data"]

        assert response.status_code == 200
        assert listed[0]["label"] == "File"
        assert listed[0]["result"]["status"] == "menu_opened"
        assert summary["counts"]["actions"] == 1


def test_v3_api_summary_includes_action_capture_breakdowns(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    image = tmp_path / "menu.png"
    image.write_bytes(b"same-frame")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/runs",
            json={
                "config": {
                    "save_root": str(tmp_path / "v3"),
                    "app_type": "pc_app",
                    "target_language": "en",
                    "must_have_text": True,
                }
            },
        ).json()["data"]
        run_id = created["run_id"]
        client.post(
            f"/api/v3/runs/{run_id}/images/ingest",
            json={"image_path": str(image), "capture_reason": "periodic", "ui_state_hint": "editor"},
        )
        client.post(
            f"/api/v3/runs/{run_id}/images/ingest",
            json={"image_path": str(image), "capture_reason": "after_action", "action_id": "action:file", "ui_state_hint": "menu_file"},
        )
        client.post(
            f"/api/v3/runs/{run_id}/actions/record",
            json={
                "action": {
                    "label": "File",
                    "source_candidate_id": "ocr_box:File:1:2:3:4",
                    "before_image": "before.png",
                    "after_image": "after.png",
                    "result": {"executed": True, "status": "menu_opened", "reason": "computer_use_click"},
                    "safety_result": {"allowed": True, "reason": "allowed"},
                }
            },
        )

        summary = client.get(f"/api/v3/runs/{run_id}/summary").json()["data"]

        assert summary["processed"] == 2
        assert summary["near_duplicate_count"] == 0
        assert summary["accepted_by_capture_reason"] == {"periodic": 1, "after_action": 1}
        assert summary["accepted_by_ui_state_hint"] == {"editor": 1, "menu_file": 1}
        assert summary["auto_click_count"] == 1
        assert summary["menu_opened_count"] == 1


def test_v3_api_summary_exposes_reject_distribution_and_production_gate(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    blank = tmp_path / "blank.png"
    blank.write_bytes(b"not-empty")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/runs",
            json={
                "config": {
                    "save_root": str(tmp_path / "v3"),
                    "target_language": "en",
                    "must_have_text": True,
                    "enable_auto_click": True,
                    "observe_only": False,
                }
            },
        ).json()["data"]
        run_id = created["run_id"]
        client.post(f"/api/v3/runs/{run_id}/images/ingest", json={"image_path": str(blank)})
        client.post(f"/api/v3/runs/{run_id}/images/ingest", json={"image_path": str(blank)})

        summary = client.get(f"/api/v3/runs/{run_id}/summary").json()["data"]

        assert summary["reject_reason_distribution"]["near_duplicate"] == 1
        assert summary["ocr_production_ready"] is False
        assert summary["full_auto_capture_ready"] is False
        assert "ocr_gpu_not_ready" in summary["readiness_blockers"]
