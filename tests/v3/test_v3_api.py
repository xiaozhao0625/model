from pathlib import Path

from fastapi.testclient import TestClient

from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings


def test_v3_api_create_start_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_INPUT_GATEWAY_DIAGNOSIS", str(tmp_path / "missing_input_gateway.json"))
    monkeypatch.setenv("APP_SHOT_OBS_OUTPUT", str(tmp_path / "obs-output"))
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/v3/health").json()
        assert health["ok"] is True
        data = health["data"]
        assert data["ocr_production_ready"] is False
        assert data["input_gateway_ready"] is False
        assert data["cursor_read_ready"] is False
        assert data["mouse_click_ready"] is False
        assert data["same_desktop_session_ready"] is False
        assert data["same_integrity_ready"] is False
        assert data["interactive_desktop_ready"] is False
        assert data["input_gateway_blockers"]
        assert data["full_auto_capture_ready"] is False
        assert data["readiness_blockers"]
        action_health = client.get("/api/v3/action/health").json()["data"]
        assert action_health["input_gateway_ready"] is False
        assert action_health["click_backend"] == "dry_run_backend"
        created = client.post("/api/v3/runs", json={"config": {"save_root": str(tmp_path / "v3")}}).json()["data"]
        started = client.post(f"/api/v3/runs/{created['run_id']}/start").json()["data"]
        summary = client.get(f"/api/v3/runs/{created['run_id']}/summary").json()["data"]
        assert started["status"] == "waiting_for_input"
        assert summary["status"] == "waiting_for_input"
        assert summary["input_status"]["status"] == "waiting_for_input"
        assert summary["observe_only"] is True


def test_v3_health_exposes_operator_status_summaries(tmp_path, monkeypatch):
    performance = tmp_path / "ocr_gpu_performance.json"
    performance.write_text(
        """
        {
          "ocr_gpu_ready": true,
          "ocr_performance_ready": true,
          "ocr_production_ready": true,
          "timings": {"full_frame_ms": 2300, "roi_ms": 420, "scaled_ms": 900, "cache_hit_ms": 4}
        }
        """,
        encoding="utf-8",
    )
    heartbeat = tmp_path / "frame_pump_heartbeat.json"
    heartbeat.write_text('{"status":"running","frame_index":12}', encoding="utf-8")
    power_active = tmp_path / "power_policy_capture_active.json"
    power_active.write_text('{"monitor_timeout_ac":0,"standby_timeout_ac":0}', encoding="utf-8")
    monkeypatch.setenv("APP_SHOT_OCR_PERFORMANCE_REPORT", str(performance))
    monkeypatch.setenv("APP_SHOT_FRAME_PUMP_HEARTBEAT", str(heartbeat))
    monkeypatch.setenv("APP_SHOT_POWER_POLICY_ACTIVE", str(power_active))
    monkeypatch.setenv("APP_SHOT_INPUT_GATEWAY_DIAGNOSIS", str(tmp_path / "missing_input_gateway.json"))
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        data = client.get("/api/v3/health").json()["data"]

        assert data["ocr_performance"]["report_path"] == str(performance)
        assert data["ocr_performance"]["full_frame_ms"] == 2300
        assert data["frame_pump"]["ready"] is True
        assert data["frame_pump"]["heartbeat_path"] == str(heartbeat)
        assert data["power_policy"]["status"] == "capture_active"
        assert data["power_policy"]["active_path"] == str(power_active)


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


def test_v3_api_rejects_unsafe_action_count_with_chinese_detail(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v3/runs",
            json={"config": {"save_root": str(tmp_path / "v3"), "app_type": "pc_app", "max_actions": 10000}},
        )
        payload = response.json()

        assert response.status_code == 422
        assert payload["ok"] is False
        assert payload["detail"][0]["field"] == "max_actions"
        assert "最大动作数是自动点击" in payload["detail"][0]["message"]


def test_v3_api_accepts_pc_game_config_fields(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v3/runs",
            json={
                "config": {
                    "save_root": str(tmp_path / "v3"),
                    "app_type": "pc_game",
                    "game_mode": "gameplay",
                    "allow_no_text_gameplay": True,
                    "enable_game_explorer": False,
                    "max_game_actions": 12,
                }
            },
        )

        assert response.status_code == 200
        config = response.json()["data"]["config"]
        assert config["app_type"] == "pc_game"
        assert config["game_mode"] == "gameplay"
        assert config["allow_no_text_gameplay"] is True
        assert config["enable_game_explorer"] is False
        assert config["max_game_actions"] == 12


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


def test_v3_api_serves_image_preview_thumbnail_and_reveal_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_DISABLE_OPEN_FOLDER", "1")
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    image = tmp_path / "accepted.png"
    image.write_bytes(b"png-bytes")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/runs",
            json={"config": {"save_root": str(tmp_path / "v3"), "target_language": "en"}},
        ).json()["data"]
        run_id = created["run_id"]
        ingested = client.post(f"/api/v3/runs/{run_id}/images/ingest", json={"image_path": str(image)}).json()["data"]
        image_id = ingested["image_id"]

        images = client.get(f"/api/v3/runs/{run_id}/images").json()["data"]
        assert images[0]["file_exists"] is True
        preview = client.get(f"/api/v3/runs/{run_id}/images/{image_id}/preview")
        thumbnail = client.get(f"/api/v3/runs/{run_id}/images/{image_id}/thumbnail")
        reveal = client.post(f"/api/v3/runs/{run_id}/images/{image_id}/reveal").json()["data"]
        open_folder = client.post(f"/api/v3/runs/{run_id}/open-folder").json()["data"]

        assert images[0]["image_id"] == image_id
        assert images[0]["absolute_path"] == str(image.resolve())
        assert preview.status_code == 200
        assert thumbnail.status_code == 200
        assert preview.content == b"png-bytes"
        assert thumbnail.content == b"png-bytes"
        assert reveal["path"] == str(image.resolve())
        assert reveal["folder"] == str(tmp_path.resolve())
        assert reveal["status"] == "disabled_by_env"
        assert open_folder["path"].endswith(run_id)
        assert open_folder["path"][1:3] == ":\\"
        assert open_folder["status"] == "disabled_by_env"

        image.unlink()
        missing_images = client.get(f"/api/v3/runs/{run_id}/images").json()["data"]
        assert missing_images[0]["file_exists"] is False


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


def test_v3_collection_multi_round_counts_unique_and_exports(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    first = tmp_path / "start_wps_001.png"
    duplicate = tmp_path / "start_wps_001_copy.png"
    second = tmp_path / "ok_wps_002.png"
    first.write_bytes(b"first-wps-screen")
    duplicate.write_bytes(b"first-wps-screen")
    second.write_bytes(b"second-wps-screen")

    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/collections",
            json={
                "config": {
                    "task_name": "wps",
                    "app_name": "WPS",
                    "app_type": "pc_app",
                    "target_language": "en",
                    "target_accepted_min": 2,
                    "target_accepted_soft": 3,
                    "save_root": str(tmp_path / "v3"),
                    "must_have_text": True,
                }
            },
        ).json()["data"]
        collection_id = created["collection_id"]

        run1 = client.post(f"/api/v3/collections/{collection_id}/continue?start=false").json()["data"]
        image1 = client.post(f"/api/v3/runs/{run1['run_id']}/images/ingest", json={"image_path": str(first)}).json()["data"]
        assert image1["bucket"] == "accepted"
        assert image1["meta"]["collection_unique"] is True

        run2 = client.post(f"/api/v3/collections/{collection_id}/continue?start=false").json()["data"]
        duplicate_image = client.post(f"/api/v3/runs/{run2['run_id']}/images/ingest", json={"image_path": str(duplicate)}).json()["data"]
        unique_image = client.post(f"/api/v3/runs/{run2['run_id']}/images/ingest", json={"image_path": str(second)}).json()["data"]

        assert duplicate_image["bucket"] == "rejected"
        assert duplicate_image["reject_reason"] == "rejected_duplicate_across_runs"
        assert duplicate_image["meta"]["duplicate_with_run_id"] == run1["run_id"]
        assert unique_image["bucket"] == "accepted"

        summary = client.get(f"/api/v3/collections/{collection_id}/summary").json()["data"]
        assert summary["run_count"] == 2
        assert summary["latest_round_accepted"] == 1
        assert summary["latest_round_duplicate_across_runs"] == 1
        assert summary["latest_round_new_unique"] == 1
        assert summary["accepted_unique_total"] == 2
        assert summary["duplicate_across_runs_total"] == 1
        assert summary["min_target_reached"] is True

        gallery = client.get(f"/api/v3/collections/{collection_id}/gallery").json()["data"]
        assert [image["image_id"] for image in gallery] == ["start_wps_001", "ok_wps_002"]

        exported = client.post(f"/api/v3/collections/{collection_id}/export").json()["data"]
        assert exported["accepted_unique_total"] == 2
        assert Path(summary["accepted_unique_dir"]).is_dir()
        assert exported["manifest_path"].endswith("manifest.json")
