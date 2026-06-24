from __future__ import annotations

from pathlib import Path

from PIL import Image

from ai_screenshot_platform.v3.game.agent_loop import GameAgentLoop
from ai_screenshot_platform.v3.game.stuck_detector import GameStuckDetector
from ai_screenshot_platform.v3.game.vision_observer import GameVisionObserver
from ai_screenshot_platform.v3 import runtime as runtime_module
from ai_screenshot_platform.v3.runtime import V3Runtime, _agent_foreground_pause_action
from ai_screenshot_platform.v3.schemas import V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore


class _ReadyInputGateway:
    input_gateway_ready = False
    real_input_allowed = True
    keyboard_input_ready = True
    mouse_move_ready = True
    mouse_move_relative_ready = True
    cursor_read_ready = False
    cursor_read_access_denied = True
    mouse_click_ready = False
    target_window_found = True
    target_window_foreground = True
    same_desktop_session_ready = True
    same_integrity_ready = True
    interactive_desktop_ready = True
    click_backend = "dry_run_backend"
    blockers = ["cursor_read_access_denied"]
    details = {"sendinput": {"callable": True}}

    def model_dump(self):
        return {
            "input_gateway_ready": self.input_gateway_ready,
            "real_input_allowed": self.real_input_allowed,
            "keyboard_input_ready": self.keyboard_input_ready,
            "mouse_move_ready": self.mouse_move_ready,
            "mouse_move_relative_ready": self.mouse_move_relative_ready,
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
            "details": self.details,
        }


class _OpenAreaObserver:
    def observe(self, **_kwargs):
        return {
            "state": "training_open_area",
            "has_text": True,
            "ocr_text": "training",
            "risk_flags": [],
            "visual_summary": "latest_frame_available",
            "last_action_effect": "changed",
            "visual_diff_score": 0.25,
            "center_diff_score": 0.18,
            "near_duplicate_ratio": 0.0,
            "repeated_frame_count": 0,
            "accepted_unique_delta_recent": 1,
            "possible_wall_ahead": False,
            "stuck_score": 0.1,
            "suggested_context": "training_open_area",
        }


def test_stuck_detector_triggers_after_repeated_forward_no_change():
    recent = [_forward_action(diff=0.01), _forward_action(diff=0.02), _forward_action(diff=0.0)]
    observation = {
        "visual_diff_score": 0.01,
        "center_diff_score": 0.01,
        "near_duplicate_ratio": 1.0,
        "repeated_frame_count": 3,
        "accepted_unique_delta_recent": 0,
        "possible_wall_ahead": True,
    }

    result = GameStuckDetector().detect(observation, recent)

    assert result["stuck"] is True
    assert result["recommended_recovery"] == "back_and_turn"
    assert result["possible_wall_ahead"] is True


def test_training_open_area_can_choose_forward(tmp_path):
    frame = _image(tmp_path / "frame.png", (40, 80, 120))
    config = _agent_config()
    agent = GameAgentLoop(allow_real_input=False)
    observation = agent.observe(config=config, before_image=str(frame), recent_actions=[], ocr_text="training range")

    plan = agent.plan(config=config, observation=observation, before_image=str(frame), recent_actions=[])

    assert observation["state"] == "training_open_area"
    assert plan["action_type"] == "key_hold"
    assert plan["keys"] == ["W"]


def test_stuck_plan_does_not_continue_forward(tmp_path):
    frame = _image(tmp_path / "same.png", (80, 80, 80))
    recent = [_forward_action(diff=0.01), _forward_action(diff=0.02), _forward_action(diff=0.0)]
    config = _agent_config()
    agent = GameAgentLoop(allow_real_input=False)
    observation = agent.observe(config=config, before_image=str(frame), previous_image=str(frame), recent_actions=recent, ocr_text="training")

    plan = agent.plan(config=config, observation=observation, before_image=str(frame), recent_actions=recent)

    assert observation["state"] in {"training_stuck", "training_blocked_ahead", "unknown_repeated"}
    assert not (plan["action_type"] == "key_hold" and plan.get("keys") == ["W"])
    assert plan["action_type"] in {"key_hold", "mouse_move_relative"}


def test_mouse_move_relative_does_not_require_cursor_read(monkeypatch):
    moves: list[tuple[int, int]] = []
    monkeypatch.setattr("ai_screenshot_platform.v3.game.agent_loop._mouse_move_relative", lambda dx, dy: moves.append((dx, dy)))
    agent = GameAgentLoop(allow_real_input=True, readiness_loader=lambda **_kwargs: _ReadyInputGateway())
    plan = {"action_type": "mouse_move_relative", "mouse_dx": 650, "mouse_dy": 0, "duration_ms": 100}

    result = agent.act(plan, config=_agent_config())

    assert result["executed"] is True
    assert moves == [(650, 0)]


def test_ui_equipment_plan_uses_keyboard_fallback_when_mouse_click_unavailable(tmp_path, monkeypatch):
    key_presses: list[list[str]] = []
    monkeypatch.setattr("ai_screenshot_platform.v3.game.agent_loop._key_press", lambda keys: key_presses.append(keys))
    frame = _image(tmp_path / "equipment.png", (120, 90, 70))
    config = _agent_config()
    agent = GameAgentLoop(allow_real_input=True, readiness_loader=lambda **_kwargs: _ReadyInputGateway())
    observation = {"state": "ui_equipment", "risk_flags": [], "stuck_score": 0.1}

    plan = agent.plan(config=config, observation=observation, before_image=str(frame), recent_actions=[])
    result = agent.act(plan, config=config)

    assert plan["action_type"] == "key_press"
    assert plan["keys"] == ["Tab"]
    assert plan["ui_explore"] is True
    assert result["executed"] is True
    assert key_presses == [["Tab"]]


def test_ui_equipment_no_change_recovers_with_escape(tmp_path):
    frame = _image(tmp_path / "equipment-stale.png", (90, 90, 90))
    config = _agent_config()
    agent = GameAgentLoop(allow_real_input=False)
    recent = [_ui_action("Tab"), _ui_action("ArrowRight"), _ui_action("ArrowDown"), _ui_action("PageDown"), _ui_action("ArrowLeft")]
    observation = {"state": "ui_equipment", "risk_flags": [], "stuck_score": 0.4}

    plan = agent.plan(config=config, observation=observation, before_image=str(frame), recent_actions=recent)

    assert plan["action_type"] == "key_press"
    assert plan["keys"] == ["Esc"]
    assert plan["ui_explore"] is True


def test_after_image_requires_fresh_frame(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_screenshot_platform.v3.game.agent_loop._key_hold", lambda _keys, _duration_ms: None)
    before = _image(tmp_path / "before.png", (20, 20, 20))
    after = _image(tmp_path / "after.png", (220, 220, 220))
    config = _agent_config()
    agent = GameAgentLoop(allow_real_input=True, readiness_loader=lambda **_kwargs: _ReadyInputGateway(), observer=_OpenAreaObserver())

    fresh = agent.step(
        collection_id="col",
        run_id="run",
        agent_step=1,
        config=config,
        before_image=str(before),
        after_image=None,
        latest_image_fn=lambda: {"path": str(after), "timestamp": before.stat().st_mtime + 1.0, "fresh": True, "timeout": False},
        action_interval_ms=300,
        recent_actions=[],
    )
    stale = agent.step(
        collection_id="col",
        run_id="run",
        agent_step=2,
        config=config,
        before_image=str(before),
        after_image=None,
        latest_image_fn=lambda: {"path": str(before), "timestamp": before.stat().st_mtime, "fresh": False, "timeout": True},
        action_interval_ms=300,
        recent_actions=[],
    )

    assert fresh["after_image"] == str(after)
    assert fresh["after_frame_fresh"] is True
    assert stale["after_image"] is None
    assert stale["after_frame_fresh"] is False
    assert stale["verify"]["status"] == "after_frame_timeout"


def test_target_window_not_foreground_pause_action_is_single_paused_record():
    action = _agent_foreground_pause_action(
        collection_id="col",
        run_id="run",
        agent_step=3,
        before_image=None,
        reason="target_window_not_foreground",
        readiness={
            "target_window_found": True,
            "target_window_foreground": False,
            "blockers": ["target_window_not_foreground"],
            "current_foreground_window": {"title": "V3 console - Google Chrome", "process_name": "chrome.exe"},
            "details": {"target_window": {"target_window": {"title": "Delta Force", "process_name": "DeltaForce.exe"}}},
        },
        focus_result={"ok": False, "blocked_reason": "target_window_not_foreground"},
    )

    assert action["agent_paused"] is True
    assert action["blocked_reason"] == "target_window_not_foreground"
    assert action["foreground_recovery_attempted"] is True
    assert action["result"]["status"] == "paused"


def test_focus_target_window_success_restarts_latest_agent_thread(tmp_path, monkeypatch):
    store = V3RunStore(tmp_path / "v3")
    collection = store.create_collection(_agent_config())
    run = store.continue_collection(collection.collection_id)
    store.update_status(run.run_id, "running")
    runtime = V3Runtime.__new__(V3Runtime)
    runtime.store = store
    runtime._game_agent_paused_reason = {run.run_id: "target_window_not_foreground"}
    runtime._game_agent_last_blocked_reason = {run.run_id: "target_window_not_foreground"}
    runtime._game_agent_threads = {}
    restarted: list[str] = []
    runtime._ensure_game_agent_thread = lambda run_id: restarted.append(run_id)  # type: ignore[method-assign]
    monkeypatch.setattr(runtime_module, "focus_target_window", lambda _config: {"ok": True, "focused": True})

    result = runtime.focus_target_window(collection.collection_id)

    assert result["ok"] is True
    assert restarted == [run.run_id]
    assert runtime._game_agent_paused_reason == {}


def test_action_history_reduces_failed_forward_weight(tmp_path):
    frame = _image(tmp_path / "frame.png", (100, 100, 100))
    recent = [_forward_action(diff=0.01), _forward_action(diff=0.0)]
    agent = GameAgentLoop(allow_real_input=False)
    config = _agent_config()
    observation = {
        "state": "training_open_area",
        "risk_flags": [],
        "visual_diff_score": 0.02,
        "center_diff_score": 0.02,
        "near_duplicate_ratio": 0.8,
        "possible_wall_ahead": False,
        "stuck_score": 0.5,
    }

    plan = agent.plan(config=config, observation=observation, before_image=str(frame), recent_actions=recent)

    assert plan["action_type"] == "mouse_move_relative"


def test_twenty_step_mock_agent_is_not_only_forward(tmp_path, monkeypatch):
    key_holds: list[str] = []
    key_presses: list[str] = []
    mouse_moves: list[tuple[int, int]] = []
    monkeypatch.setattr("ai_screenshot_platform.v3.game.agent_loop._key_hold", lambda keys, duration_ms: key_holds.extend(keys))
    monkeypatch.setattr("ai_screenshot_platform.v3.game.agent_loop._key_press", lambda keys: key_presses.extend(keys))
    monkeypatch.setattr("ai_screenshot_platform.v3.game.agent_loop._mouse_move_relative", lambda dx, dy: mouse_moves.append((dx, dy)))
    config = _agent_config()
    agent = GameAgentLoop(allow_real_input=True, readiness_loader=lambda **_kwargs: _ReadyInputGateway(), observer=_OpenAreaObserver())
    actions: list[dict[str, object]] = []

    for index in range(20):
        before = _image(tmp_path / f"before_{index}.png", ((index * 7) % 255, 80, 120))
        after = _image(tmp_path / f"after_{index}.png", (((index * 7) + 40) % 255, 120, 80))
        action = agent.step(
            collection_id="col",
            run_id="run",
            agent_step=index + 1,
            config=config,
            before_image=str(before),
            after_image=None,
            latest_image_fn=lambda path=str(after): path,
            action_interval_ms=300,
            recent_actions=actions,
        )
        actions.append(action)

    action_types = [str(action["action_type"]) for action in actions]
    key_counts = [key.upper() for key in key_holds + key_presses]

    assert "key_hold" in action_types
    assert "W" in key_counts
    assert "mouse_move_relative" in action_types
    assert mouse_moves
    assert any(key in {"TAB", "ESC"} for key in key_counts)
    assert action_types.count("key_hold") < 20


def _agent_config() -> V3TaskConfig:
    return V3TaskConfig(
        app_type="pc_game",
        enable_game_agent=True,
        game_agent_mode="auto_explore",
        safe_scene_confirmed=True,
        allow_wasd=True,
        allow_hotkeys=True,
        allow_mouse_look=True,
        allow_inventory_map_explore=True,
        allow_back_close=True,
        allow_training_movement=True,
        action_interval_ms=300,
    )


def _forward_action(diff: float) -> dict[str, object]:
    return {
        "action_id": "game_agent_test",
        "action_type": "key_hold",
        "keys": ["W"],
        "visual_diff_score": diff,
        "verify": {"status": "no_visual_change" if diff < 0.08 else "changed", "visual_diff_score": diff, "changed": diff >= 0.08},
        "accepted_unique_delta": 0,
    }


def _ui_action(key: str) -> dict[str, object]:
    return {
        "action_id": "game_agent_ui",
        "action_type": "key_press",
        "keys": [key],
        "observed_state": "ui_equipment",
        "ui_explore": True,
        "visual_diff_score": 0.01,
        "verify": {"status": "no_visual_change", "visual_diff_score": 0.01, "changed": False},
        "accepted_unique_delta": 0,
    }


def _image(path: Path, color: tuple[int, int, int]) -> Path:
    Image.new("RGB", (96, 96), color).save(path)
    return path
