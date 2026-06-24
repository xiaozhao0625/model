from pathlib import Path

from fastapi.testclient import TestClient

from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings
from ai_screenshot_platform.v3.game import agent_loop as game_agent_module
from ai_screenshot_platform.v3.schemas import V3TaskConfig


class _ReadyInputGateway:
    input_gateway_ready = True
    real_input_allowed = True
    keyboard_input_ready = True
    mouse_move_ready = True
    cursor_read_ready = True
    cursor_read_access_denied = False
    mouse_click_ready = True
    target_window_found = True
    target_window_foreground = True
    same_desktop_session_ready = True
    same_integrity_ready = True
    interactive_desktop_ready = True
    click_backend = "computer_use_backend"
    blockers = []

    def model_dump(self):
        return {
            "input_gateway_ready": self.input_gateway_ready,
            "real_input_allowed": self.real_input_allowed,
            "keyboard_input_ready": self.keyboard_input_ready,
            "mouse_move_ready": self.mouse_move_ready,
            "cursor_read_ready": self.cursor_read_ready,
            "cursor_read_access_denied": self.cursor_read_access_denied,
            "mouse_click_ready": self.mouse_click_ready,
            "target_window_found": self.target_window_found,
            "target_window_foreground": self.target_window_foreground,
            "same_desktop_session_ready": self.same_desktop_session_ready,
            "same_integrity_ready": self.same_integrity_ready,
            "interactive_desktop_ready": self.interactive_desktop_ready,
            "click_backend": self.click_backend,
            "blockers": self.blockers,
        }


def test_v3_api_create_start_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_INPUT_GATEWAY_DIAGNOSIS", str(tmp_path / "missing_input_gateway.json"))
    monkeypatch.setenv("APP_SHOT_OBS_OUTPUT", str(tmp_path / "obs-output"))
    monkeypatch.setenv("APP_SHOT_DISABLE_FRAME_PUMP", "1")
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
        assert data["real_input_enabled"] is False
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


def test_v3_frame_pump_api_status_start_stop(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_OBS_OUTPUT", str(tmp_path / "obs-output"))
    monkeypatch.setenv("APP_SHOT_DISABLE_FRAME_PUMP", "1")
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        status = client.get("/api/v3/frame-pump/status").json()["data"]
        assert status["status"] == "stopped"
        assert status["output_dir"] == str(tmp_path / "obs-output")

        started = client.post("/api/v3/frame-pump/start", json={"fps": 2, "full_screen": True}).json()["data"]
        assert started["status"] == "stopped"
        assert "disabled" in started["message"]

        stopped = client.post("/api/v3/frame-pump/stop").json()["data"]
        assert stopped["status"] == "stopped"


def test_v3_collection_creates_dedicated_input_dir_and_opens_it(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_OBS_OUTPUT", str(tmp_path / "obs-output"))
    monkeypatch.setenv("APP_SHOT_DISABLE_OPEN_FOLDER", "1")
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/collections",
            json={
                "config": {
                    "task_name": "三角洲",
                    "app_name": "三角洲",
                    "app_type": "pc_game",
                    "save_root": str(tmp_path / "v3"),
                }
            },
        ).json()["data"]
        collection_id = created["collection_id"]
        summary = client.get(f"/api/v3/collections/{collection_id}/summary").json()["data"]
        opened = client.post(f"/api/v3/collections/{collection_id}/open-input-folder?dry_run=true").json()["data"]

        assert summary["input_dir"] == summary["watch_dir"] == summary["frame_pump_output_dir"]
        assert summary["input_dir"].startswith(str(tmp_path / "obs-output"))
        assert "三角洲" in Path(summary["input_dir"]).name
        assert Path(summary["input_dir"]).is_dir()
        assert opened["path"] == summary["input_dir"]
        assert opened["status"] == "dry_run"


def test_v3_collection_target_window_api_persists_and_health_is_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_OBS_OUTPUT", str(tmp_path / "obs-output"))
    monkeypatch.setenv("APP_SHOT_INPUT_GATEWAY_DIAGNOSIS", str(tmp_path / "missing_input_gateway.json"))
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/collections",
            json={
                "config": {
                    "task_name": "target_window_case",
                    "app_name": "target_window_case",
                    "app_type": "pc_game",
                    "save_root": str(tmp_path / "v3"),
                }
            },
        ).json()["data"]
        collection_id = created["collection_id"]

        windows = client.get("/api/v3/action/windows").json()
        assert windows["ok"] is True
        assert isinstance(windows["data"], list)

        updated = client.post(
            f"/api/v3/collections/{collection_id}/target-window",
            json={"hwnd": 12345, "title": "Target Game", "process_name": "target.exe", "pid": 456},
        ).json()["data"]
        health = client.get(f"/api/v3/action/health?collection_id={collection_id}").json()["data"]
        focused = client.post("/api/v3/action/focus-target-window", json={"collection_id": collection_id}).json()["data"]

        assert updated["target_window_hwnd"] == 12345
        assert updated["target_window_title"] == "Target Game"
        assert updated["target_process_name"] == "target.exe"
        assert updated["target_process_id"] == 456
        assert health["target_window_found"] is False
        assert "target_window_not_found" in health["blockers"]
        assert focused["ok"] is False
        assert focused["blocked_reason"] == "target_window_not_found"


def test_v3_frame_pump_start_accepts_explicit_output_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_DISABLE_FRAME_PUMP", "1")
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    output_dir = tmp_path / "obs-output" / "collection_a"
    with TestClient(create_app(settings)) as client:
        started = client.post(
            "/api/v3/frame-pump/start",
            json={"fps": 1, "source_mode": "obs_websocket", "output_dir": str(output_dir)},
        ).json()["data"]

        assert started["status"] == "stopped"
        assert started["output_dir"] == str(output_dir)
        assert "disabled" in started["message"]


def test_v3_collection_export_without_unique_images_returns_chinese_error(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/collections",
            json={"config": {"task_name": "empty_export", "app_name": "empty_export", "save_root": str(tmp_path / "v3")}},
        ).json()["data"]
        payload = client.post(f"/api/v3/collections/{created['collection_id']}/export").json()

        assert payload["ok"] is False
        assert payload["error_code"] == "no_accepted_unique_images"
        assert "当前没有最终有效图" in payload["message"]


def test_v3_game_agent_start_records_blocked_reason_when_no_frame(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_DISABLE_FRAME_PUMP", "1")
    monkeypatch.delenv("APP_SHOT_ALLOW_REAL_INPUT", raising=False)
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/collections",
            json={
                "start_immediately": True,
                "config": {
                    "task_name": "agent_case",
                    "app_name": "agent_case",
                    "app_type": "pc_game",
                    "save_root": str(tmp_path / "v3"),
                    "enable_game_agent": True,
                    "game_agent_mode": "auto_explore",
                    "safe_scene_confirmed": True,
                    "allow_hotkeys": True,
                    "allow_wasd": True,
                    "action_interval_ms": 300,
                },
            },
        ).json()["data"]
        run_id = created["run"]["run_id"]
        actions = []
        for _ in range(20):
            actions = client.get(f"/api/v3/runs/{run_id}/actions").json()["data"]
            if actions:
                break
            import time

            time.sleep(0.1)
        summary = client.get(f"/api/v3/collections/{created['collection']['collection_id']}/summary").json()["data"]

        assert actions
        assert actions[0]["executed"] is False
        assert actions[0]["blocked_reason"] == "real_input_disabled"
        assert summary["game_agent_status"] == "已启用，但真实输入未授权"
        assert "WASD" in summary["game_agent_enabled_capabilities"]
        assert summary["real_input_enabled"] is False


def test_v3_agent_config_patch_persists_and_continue_inherits(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_RUNS", str(tmp_path / "v3"))
    monkeypatch.setenv("APP_SHOT_DISABLE_FRAME_PUMP", "1")
    monkeypatch.delenv("APP_SHOT_ALLOW_REAL_INPUT", raising=False)
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/collections",
            json={
                "config": {
                    "task_name": "agent_patch",
                    "app_name": "agent_patch",
                    "app_type": "pc_game",
                    "save_root": str(tmp_path / "v3"),
                }
            },
        ).json()["data"]
        collection_id = created["collection_id"]

        patched = client.patch(
            f"/api/v3/collections/{collection_id}/agent-config",
            json={
                "enable_game_agent": True,
                "allow_ui_click": True,
                "allow_hotkeys": True,
                "allow_wasd": True,
                "allow_mouse_look": True,
                "allow_inventory_map_explore": True,
                "safe_scene_confirmed": True,
                "action_interval_ms": 1500,
            },
        ).json()["data"]

        assert patched["enable_game_agent"] is True
        assert patched["game_agent_mode"] == "auto_explore"
        assert patched["allow_wasd"] is True
        assert patched["allow_mouse_look"] is True
        assert patched["safe_scene_confirmed"] is True
        assert patched["game_agent_status"] == "已启用，但真实输入未授权"
        assert "WASD" in patched["game_agent_enabled_capabilities"]
        assert "鼠标视角" in patched["game_agent_enabled_capabilities"]

        collection_file = tmp_path / "v3" / "collections" / collection_id / "collection.json"
        text = collection_file.read_text(encoding="utf-8")
        assert '"enable_game_agent": true' in text
        assert '"allow_wasd": true' in text
        assert '"allow_mouse_look": true' in text

        run = client.post(f"/api/v3/collections/{collection_id}/continue?start=false").json()["data"]
        assert run["config"]["enable_game_agent"] is True
        assert run["config"]["allow_wasd"] is True
        assert run["config"]["allow_mouse_look"] is True
        assert run["config"]["safe_scene_confirmed"] is True


def test_v3_agent_config_patch_disable_clears_capabilities(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_RUNS", str(tmp_path / "v3"))
    monkeypatch.setenv("APP_SHOT_DISABLE_FRAME_PUMP", "1")
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/collections",
            json={
                "config": {
                    "task_name": "agent_disable",
                    "app_name": "agent_disable",
                    "app_type": "pc_game",
                    "save_root": str(tmp_path / "v3"),
                    "enable_game_agent": True,
                    "allow_wasd": True,
                    "allow_mouse_look": True,
                    "safe_scene_confirmed": True,
                }
            },
        ).json()["data"]
        collection_id = created["collection_id"]

        disabled = client.patch(f"/api/v3/collections/{collection_id}/agent-config", json={"enable_game_agent": False}).json()["data"]

        assert disabled["enable_game_agent"] is False
        assert disabled["game_agent_status"] == "未启用"
        assert disabled["allow_wasd"] is False
        assert disabled["allow_mouse_look"] is False
        assert disabled["game_agent_enabled_capabilities"] == []


def test_v3_game_agent_authorized_input_can_execute_without_real_keyboard(tmp_path, monkeypatch):
    before = tmp_path / "before.png"
    after = tmp_path / "after.png"
    before.write_bytes(b"before")
    after.write_bytes(b"after")
    calls: list[tuple[list[str], int]] = []
    monkeypatch.setattr(game_agent_module, "_key_hold", lambda keys, duration_ms: calls.append((keys, duration_ms)))
    agent = game_agent_module.GameAgentLoop(allow_real_input=True, readiness_loader=lambda: _ReadyInputGateway())

    action = agent.step(
        collection_id="col_exec",
        run_id="run_exec",
        agent_step=1,
        config=V3TaskConfig(
            app_type="pc_game",
            enable_game_agent=True,
            game_agent_mode="auto_explore",
            safe_scene_confirmed=True,
            allow_wasd=True,
            allow_hotkeys=True,
            action_interval_ms=300,
        ),
        before_image=str(before),
        after_image=None,
        latest_image_fn=lambda: str(after),
        action_interval_ms=300,
    )

    assert action["executed"] is True
    assert action["blocked_reason"] is None
    assert action["planned_action"] == "key_hold"
    assert calls == [(["W"], 800)]


def test_v3_runs_list_skips_corrupt_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_RUNS", str(tmp_path / "runs"))
    monkeypatch.setenv("APP_SHOT_OBS_OUTPUT", str(tmp_path / "obs-output"))
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    corrupt_dir = tmp_path / "runs" / "v3" / "v3_corrupt"
    corrupt_dir.mkdir(parents=True)
    (corrupt_dir / "run.json").write_bytes(b"\x00" * 128)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v3/runs")
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"] == []
    audit = tmp_path / "runs" / "v3" / "trash" / "corrupt_metadata_audit.jsonl"
    assert audit.is_file()
    assert "v3_corrupt" in audit.read_text(encoding="utf-8")


def test_v3_obs_api_returns_friendly_status_without_obs(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_OBS_OUTPUT", str(tmp_path / "obs-output"))
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        unavailable_port = 9
        status = client.get(f"/api/v3/obs/status?obs_port={unavailable_port}").json()["data"]
        scenes = client.get(f"/api/v3/obs/scenes?obs_port={unavailable_port}").json()["data"]
        sources = client.get(f"/api/v3/obs/sources?obs_port={unavailable_port}").json()["data"]
        shot = client.post("/api/v3/obs/test-screenshot", json={"obs_host": "127.0.0.1", "obs_port": unavailable_port}).json()["data"]

        assert status["connected"] is False
        assert status["error"]
        assert scenes["scenes"] == []
        assert sources["sources"] == []
        assert shot["ok"] is False
        assert shot["source_mode"] == "obs_websocket"


def test_v3_delete_restore_collection_and_delete_run_recalculates(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SHOT_DISABLE_OPEN_FOLDER", "1")
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    image1 = tmp_path / "start_wps_001.png"
    image2 = tmp_path / "ok_wps_002.png"
    image1.write_bytes(b"first-wps-screen")
    image2.write_bytes(b"second-wps-screen")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/collections",
            json={
                "config": {
                    "task_name": "delete_case",
                    "app_name": "delete_case",
                    "target_language": "en",
                    "save_root": str(tmp_path / "v3"),
                    "must_have_text": True,
                }
            },
        ).json()["data"]
        collection_id = created["collection_id"]
        run1 = client.post(f"/api/v3/collections/{collection_id}/continue?start=false").json()["data"]
        run2 = client.post(f"/api/v3/collections/{collection_id}/continue?start=false").json()["data"]
        client.post(f"/api/v3/runs/{run1['run_id']}/images/ingest", json={"image_path": str(image1)})
        client.post(f"/api/v3/runs/{run2['run_id']}/images/ingest", json={"image_path": str(image2)})

        before = client.get(f"/api/v3/collections/{collection_id}/summary").json()["data"]
        assert before["run_count"] == 2
        assert before["accepted_unique_total"] == 2

        deleted_run = client.delete(f"/api/v3/runs/{run2['run_id']}").json()["data"]
        after_run_delete = client.get(f"/api/v3/collections/{collection_id}/summary").json()["data"]
        assert deleted_run["status"] == "deleted"
        assert after_run_delete["run_count"] == 1
        assert after_run_delete["accepted_unique_total"] == 1

        deleted = client.delete(f"/api/v3/collections/{collection_id}").json()["data"]
        assert deleted["status"] == "deleted"
        assert all(item["collection_id"] != collection_id for item in client.get("/api/v3/collections").json()["data"])
        assert any(item["collection_id"] == collection_id for item in client.get("/api/v3/collections?include_deleted=true").json()["data"])

        restored = client.post(f"/api/v3/collections/{collection_id}/restore").json()["data"]
        assert restored["status"] == "stopped"
        assert any(item["collection_id"] == collection_id for item in client.get("/api/v3/collections").json()["data"])


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


def test_v3_collection_summary_splits_attempt_executed_blocked_actions(tmp_path):
    settings = MasterSettings(database_url=f"sqlite:///{tmp_path / 'master.db'}")
    with TestClient(create_app(settings)) as client:
        created = client.post(
            "/api/v3/collections",
            json={"config": {"task_name": "action_stats", "app_name": "action_stats", "save_root": str(tmp_path / "v3")}},
        ).json()["data"]
        collection_id = created["collection_id"]
        run = client.post(f"/api/v3/collections/{collection_id}/continue?start=false").json()["data"]

        client.post(
            f"/api/v3/runs/{run['run_id']}/actions/record",
            json={
                "action": {
                    "action_type": "key_hold",
                    "result": {"executed": True, "status": "executed"},
                    "executed": True,
                }
            },
        )
        client.post(
            f"/api/v3/runs/{run['run_id']}/actions/record",
            json={
                "action": {
                    "action_type": "mouse_click",
                    "blocked_reason": "cursor_read_access_denied",
                    "result": {"executed": False, "status": "blocked", "reason": "cursor_read_access_denied"},
                    "executed": False,
                }
            },
        )

        summary = client.get(f"/api/v3/collections/{collection_id}/summary").json()["data"]

        assert summary["latest_round_action_attempt_count"] == 2
        assert summary["latest_round_action_executed_count"] == 1
        assert summary["latest_round_action_blocked_count"] == 1
        assert summary["action_attempt_total"] == 2
        assert summary["action_executed_total"] == 1
        assert summary["action_blocked_total"] == 1
        assert summary["latest_blocked_reason"] == "cursor_read_access_denied"


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
        opened_export = client.post(f"/api/v3/collections/{collection_id}/open-export-folder?dry_run=true").json()["data"]
        assert exported["accepted_unique_total"] == 2
        assert exported["zip_path"].endswith(".zip")
        assert Path(summary["accepted_unique_dir"]).is_dir()
        assert exported["manifest_path"].endswith("manifest.json")
        assert opened_export["path"] == summary["export_dir"]
