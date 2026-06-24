from __future__ import annotations

import ctypes
import os
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from ai_screenshot_platform.v3.action.input_gateway import blocked_reason_for_action, load_input_gateway_readiness
from ai_screenshot_platform.v3.game.stuck_detector import GameStuckDetector
from ai_screenshot_platform.v3.game.vision_observer import GameVisionObserver, compare_frames
from ai_screenshot_platform.v3.schemas import V3TaskConfig, utc_now


RISK_STATES = {"risk_page", "login", "shop", "payment", "matchmaking", "ranked", "chat", "account", "captcha", "uac", "secure_desktop"}
RECOVERY_STATES = {"training_blocked_ahead", "training_stuck", "gameplay_no_change", "unknown_repeated"}
OPEN_AREA_STATES = {"training_open_area", "gameplay_moving", "hud_with_text", "unknown_safe"}
UI_STATES = {"ui_inventory", "ui_warehouse", "ui_equipment", "ui_settings", "ui_mission", "ui_map"}


class GameAgentLoop:
    def __init__(
        self,
        *,
        allow_real_input: bool | None = None,
        readiness_loader: Callable[..., object] = load_input_gateway_readiness,
        observer: GameVisionObserver | None = None,
        stuck_detector: GameStuckDetector | None = None,
    ) -> None:
        self.allow_real_input = (
            os.environ.get("APP_SHOT_ALLOW_REAL_INPUT", "").strip() == "1"
            if allow_real_input is None
            else allow_real_input
        )
        self.readiness_loader = readiness_loader
        self.observer = observer or GameVisionObserver()
        self.stuck_detector = stuck_detector or GameStuckDetector()
        self.last_actions: list[dict[str, object]] = []
        self.last_action_effects: list[str] = []

    def observe(
        self,
        *,
        config: V3TaskConfig,
        before_image: str | None,
        previous_image: str | None = None,
        recent_actions: list[dict[str, object]] | None = None,
        ocr_text: str = "",
        last_action_effect: str | None = None,
    ) -> dict[str, object]:
        return self.observer.observe(
            config=config,
            current_frame=before_image,
            previous_frame=previous_image,
            recent_actions=recent_actions or self.last_actions,
            ocr_text=ocr_text,
            last_action_effect=last_action_effect,
        )

    def classify_state(self, *, ocr_text: str, config: V3TaskConfig) -> str:
        return str(self.observe(config=config, before_image=None, ocr_text=ocr_text).get("state") or "unknown_safe")

    def plan(
        self,
        *,
        config: V3TaskConfig,
        observation: dict[str, object],
        before_image: str | None,
        recent_actions: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        recent_actions = recent_actions or self.last_actions
        state = str(observation.get("state") or "unknown_safe")
        if not config.enable_game_agent and not config.enable_game_explorer:
            return self._blocked_plan("wait", "game_agent_disabled", state)
        if not (config.safe_scene_confirmed or config.safe_game_scene_confirmed):
            return self._blocked_plan("wait", "safe_scene_not_confirmed", state)
        if state in RISK_STATES or observation.get("risk_flags"):
            return self._blocked_plan("wait", f"unsafe_state_{state}", state)
        if not self._has_any_capability(config):
            return self._blocked_plan("wait", "no_action_capability_enabled", state)
        if not before_image:
            disabled_probe = self._real_input_disabled_probe_plan(config, state)
            if disabled_probe is not None:
                return disabled_probe
            return self._blocked_plan("wait", "frame_pump_no_frame", state)

        stuck = self.stuck_detector.detect(observation, recent_actions)
        if stuck["stuck"] and state not in UI_STATES:
            state = "training_stuck" if state.startswith("training") or config.allow_training_movement else "gameplay_no_change"

        if state in UI_STATES:
            return self._ui_plan(config, state, recent_actions)
        if state in RECOVERY_STATES:
            return self._recovery_plan(config, state, recent_actions, observation)
        if state in OPEN_AREA_STATES:
            return self._open_area_plan(config, state, recent_actions)
        return self._unknown_plan(config, state, recent_actions)

    def act(self, plan: dict[str, object], *, config: V3TaskConfig | None = None) -> dict[str, object]:
        blocked_reason = plan.get("blocked_reason")
        if blocked_reason:
            return {"executed": False, "reason": blocked_reason, "status": "blocked"}
        if not self.allow_real_input:
            return {"executed": False, "reason": "real_input_disabled", "status": "blocked"}
        action_type = str(plan.get("action_type") or "wait")
        readiness = self._readiness_for_config(config)
        blocked = blocked_reason_for_action(action_type, readiness)
        if blocked:
            blockers = getattr(readiness, "blockers", []) or []
            readiness_payload = readiness.model_dump() if hasattr(readiness, "model_dump") else {}
            return {"executed": False, "reason": blocked, "status": "blocked", "blockers": blockers, "readiness": readiness_payload}
        try:
            if action_type == "key_hold":
                _key_hold([str(key) for key in plan.get("keys", [])], int(plan.get("duration_ms") or 500))
            elif action_type in {"key_press", "hotkey"}:
                _key_press([str(key) for key in plan.get("keys", [])])
            elif action_type in {"mouse_move_relative", "mouse_move_small", "mouse_move"}:
                _mouse_move_relative(int(plan.get("mouse_dx") or 0), int(plan.get("mouse_dy") or 0))
            elif action_type == "wait":
                time.sleep(max(0.05, int(plan.get("duration_ms") or 100) / 1000))
            else:
                return {"executed": False, "reason": f"unsupported_action:{action_type}", "status": "blocked"}
        except Exception as exc:  # pragma: no cover - depends on interactive desktop.
            return {"executed": False, "reason": f"input_execution_failed:{exc}", "status": "error"}
        return {"executed": True, "reason": "real_input_executed", "status": "executed"}

    def verify(self, *, before_image: str | None, after_image: str | None) -> dict[str, object]:
        before_sha = _file_sha256(before_image)
        after_sha = _file_sha256(after_image)
        features = compare_frames(before_image, after_image)
        visual_diff = float(features.get("visual_diff_score") or 0.0)
        center_diff = float(features.get("center_diff_score") or 0.0)
        changed = bool((visual_diff >= 0.08 or center_diff >= 0.05) or (before_sha and after_sha and before_sha != after_sha and visual_diff == 0.0))
        status = "changed" if changed else "no_visual_change"
        return {
            "before_sha256": before_sha,
            "after_sha256": after_sha,
            "changed": changed,
            "status": status,
            **features,
        }

    def step(
        self,
        *,
        collection_id: str | None,
        run_id: str,
        agent_step: int,
        config: V3TaskConfig,
        before_image: str | None,
        after_image: str | None,
        latest_image_fn: Callable[[], str | None] | None = None,
        action_interval_ms: int = 1500,
        ocr_text: str = "",
        last_action_effect: str | None = None,
        recent_actions: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        recent_actions = (recent_actions or self.last_actions)[-12:]
        previous_image = _last_frame_from_actions(recent_actions)
        observation = self.observe(
            config=config,
            before_image=before_image,
            previous_image=previous_image,
            recent_actions=recent_actions,
            ocr_text=ocr_text,
            last_action_effect=last_action_effect,
        )
        plan = self.plan(config=config, observation=observation, before_image=before_image, recent_actions=recent_actions)
        result = self.act(plan, config=config)
        if latest_image_fn is not None:
            time.sleep(max(0.1, action_interval_ms / 1000))
            after_image = latest_image_fn()
        verify = self.verify(before_image=before_image, after_image=after_image)
        blocked_reason = plan.get("blocked_reason") or (None if result.get("executed") else result.get("reason"))
        stuck_before = float(observation.get("stuck_score") or 0.0)
        stuck_after = _stuck_after(stuck_before, verify)
        action = {
            "action_id": f"game_agent_{uuid.uuid4().hex[:12]}",
            "collection_id": collection_id,
            "run_id": run_id,
            "agent_step": agent_step,
            "observed_state": observation["state"],
            "observation": observation,
            "planned_action": plan.get("planned_action"),
            "action_type": plan.get("action_type"),
            "keys": plan.get("keys", []),
            "duration_ms": plan.get("duration_ms"),
            "mouse_dx": plan.get("mouse_dx", 0),
            "mouse_dy": plan.get("mouse_dy", 0),
            "reason": plan.get("reason"),
            "next_plan": plan.get("next_plan") or plan.get("planned_action"),
            "next_plan_reason": plan.get("reason"),
            "executed": bool(result.get("executed")),
            "blocked_reason": str(blocked_reason) if blocked_reason else None,
            "before_image": before_image,
            "after_image": after_image,
            "visual_diff_score": verify["visual_diff_score"],
            "center_diff_score": verify.get("center_diff_score", 0.0),
            "stuck_score_before": stuck_before,
            "stuck_score_after": stuck_after,
            "possible_wall_ahead": bool(observation.get("possible_wall_ahead")),
            "verify": verify,
            "result": result,
            "created_at": utc_now(),
        }
        self._remember_action(action)
        return action

    def _open_area_plan(self, config: V3TaskConfig, state: str, recent_actions: list[dict[str, object]]) -> dict[str, object]:
        step_index = _agent_step_index(recent_actions)
        if config.allow_back_close and config.allow_hotkeys and step_index > 0 and step_index % 12 == 0:
            return self._key_plan("Esc", 80, "periodic_safe_close_panel", state)
        if config.allow_inventory_map_explore and config.allow_hotkeys and step_index > 0 and step_index % 8 == 0:
            return self._key_plan("Tab", 80, "periodic_panel_explore_for_text", state)
        if config.allow_mouse_look and step_index > 0 and step_index % 5 == 0:
            direction = -450 if _last_mouse_dx(recent_actions) > 0 else 450
            return self._mouse_plan(direction, 0, 220, "periodic_visual_scan", state)
        if config.allow_mouse_look and self._ineffective_repeats("key_hold:W", recent_actions) >= 2:
            return self._mouse_plan(650, 0, 250, "forward_no_change_turn_right", state)
        if (config.allow_wasd or config.allow_training_movement) and self._ineffective_repeats("key_hold:W", recent_actions) < 2:
            return self._key_plan("W", 800, "open_area_forward_probe", state, hold=True)
        if config.allow_mouse_look:
            direction = -500 if _last_mouse_dx(recent_actions) > 0 else 500
            return self._mouse_plan(direction, 0, 220, "scan_open_area", state)
        if config.allow_wasd or config.allow_training_movement:
            return self._key_plan("D", 350, "open_area_strafe_probe", state, hold=True)
        return self._unknown_plan(config, state, recent_actions)

    def _recovery_plan(
        self,
        config: V3TaskConfig,
        state: str,
        recent_actions: list[dict[str, object]],
        observation: dict[str, object],
    ) -> dict[str, object]:
        last_key = _action_key(recent_actions[-1]) if recent_actions else ""
        if (config.allow_wasd or config.allow_training_movement) and last_key not in {"key_hold:S", "mouse_move_relative"}:
            return self._key_plan("S", 500, "stuck_recovery_back_up", state, hold=True)
        if config.allow_mouse_look and last_key != "mouse_move_relative":
            return self._mouse_plan(800, 0, 250, "blocked_ahead_turn_right", state)
        if (config.allow_wasd or config.allow_training_movement) and last_key != "key_hold:D":
            return self._key_plan("D", 450, "stuck_recovery_strafe_right", state, hold=True)
        if config.allow_mouse_look:
            return self._mouse_plan(-1200, 0, 300, "still_stuck_turn_left_wider", state)
        if config.allow_hotkeys and config.allow_inventory_map_explore:
            return self._key_plan("M", 80, "still_repeated_open_map_for_text", state)
        return self._blocked_plan("wait", "no_recovery_capability_enabled", state)

    def _ui_plan(self, config: V3TaskConfig, state: str, recent_actions: list[dict[str, object]]) -> dict[str, object]:
        if state == "ui_map" and config.allow_hotkeys:
            return self._key_plan("M", 80, "toggle_map_for_coverage", state)
        if state in {"ui_inventory", "ui_warehouse", "ui_equipment"} and config.allow_hotkeys:
            return self._key_plan("Tab", 80, "switch_inventory_panel", state)
        if state in {"ui_settings", "ui_mission"} and config.allow_back_close and config.allow_hotkeys:
            return self._key_plan("Esc", 80, "close_low_risk_ui_page", state)
        if config.allow_hotkeys:
            return self._key_plan("Tab", 80, "safe_ui_hotkey_explore", state)
        return self._blocked_plan("wait", "ui_page_no_hotkey_capability", state)

    def _unknown_plan(self, config: V3TaskConfig, state: str, recent_actions: list[dict[str, object]]) -> dict[str, object]:
        if config.allow_mouse_look:
            return self._mouse_plan(900, 0, 250, "unknown_or_repeated_turn_to_find_new_view", state)
        if config.allow_wasd or config.allow_training_movement:
            return self._key_plan("A", 350, "unknown_or_repeated_strafe_probe", state, hold=True)
        if config.allow_hotkeys:
            return self._key_plan("Tab", 80, "unknown_safe_panel_probe", state)
        return self._blocked_plan("wait", "no_safe_plan_for_state", state)

    def _key_plan(self, key: str, duration_ms: int, reason: str, state: str, *, hold: bool = False) -> dict[str, object]:
        action_type = "key_hold" if hold else "key_press"
        return {
            "action_type": action_type,
            "planned_action": action_type,
            "keys": [key],
            "duration_ms": duration_ms,
            "reason": reason,
            "observed_state": state,
            "next_plan": action_type,
        }

    def _mouse_plan(self, dx: int, dy: int, duration_ms: int, reason: str, state: str) -> dict[str, object]:
        return {
            "action_type": "mouse_move_relative",
            "planned_action": "mouse_move_relative",
            "mouse_dx": dx,
            "mouse_dy": dy,
            "duration_ms": duration_ms,
            "reason": reason,
            "observed_state": state,
            "next_plan": "mouse_move_relative",
        }

    def _blocked_plan(self, action_type: str, reason: str, state: str) -> dict[str, object]:
        return {
            "action_type": action_type,
            "planned_action": action_type,
            "reason": reason,
            "blocked_reason": reason,
            "observed_state": state,
            "next_plan": action_type,
        }

    def _real_input_disabled_probe_plan(self, config: V3TaskConfig, state: str) -> dict[str, object] | None:
        if self.allow_real_input:
            return None
        if config.allow_mouse_look:
            return self._mouse_plan(300, 0, 120, "real_input_disabled", state)
        if config.allow_wasd or config.allow_training_movement:
            return self._key_plan("W", 500, "real_input_disabled", state, hold=True)
        if config.allow_hotkeys:
            return self._key_plan("Tab", 80, "real_input_disabled", state)
        if config.allow_ui_click or config.enable_auto_click:
            return {"action_type": "ui_click", "planned_action": "ui_click", "duration_ms": 80, "reason": "real_input_disabled", "observed_state": state}
        return None

    def _readiness_for_config(self, config: V3TaskConfig | None):
        try:
            return self.readiness_loader(target_config=config)
        except TypeError:
            return self.readiness_loader()

    def _has_any_capability(self, config: V3TaskConfig) -> bool:
        return any(
            [
                config.allow_ui_click or config.enable_auto_click,
                config.allow_hotkeys,
                config.allow_wasd,
                config.allow_mouse_look,
                config.allow_back_close,
                config.allow_inventory_map_explore,
                config.allow_training_movement,
            ]
        )

    def _ineffective_repeats(self, action_key: str, recent_actions: list[dict[str, object]]) -> int:
        count = 0
        for action in reversed(recent_actions[-5:]):
            if _action_key(action) != action_key:
                break
            verify = action.get("verify")
            status = str(verify.get("status") if isinstance(verify, dict) else action.get("verify_status") or "")
            diff = float(action.get("visual_diff_score") or (verify.get("visual_diff_score") if isinstance(verify, dict) else 0.0) or 0.0)
            accepted_delta = int(action.get("accepted_unique_delta") or 0)
            if status in {"no_visual_change", "stuck"} or (diff < 0.08 and accepted_delta == 0):
                count += 1
        return count

    def _remember_action(self, action: dict[str, object]) -> None:
        self.last_actions = (self.last_actions + [action])[-10:]
        verify = action.get("verify")
        effect = str(verify.get("status") if isinstance(verify, dict) else "unknown")
        self.last_action_effects = (self.last_action_effects + [effect])[-10:]


_VK = {
    "W": 0x57,
    "A": 0x41,
    "S": 0x53,
    "D": 0x44,
    "M": 0x4D,
    "I": 0x49,
    "B": 0x42,
    "TAB": 0x09,
    "ESC": 0x1B,
    "SPACE": 0x20,
}


def _key_hold(keys: list[str], duration_ms: int) -> None:
    for key in keys:
        _key_event(key, down=True)
    time.sleep(max(0.01, duration_ms / 1000))
    for key in reversed(keys):
        _key_event(key, down=False)


def _key_press(keys: list[str]) -> None:
    for key in keys:
        _key_hold([key], 80)


def _key_event(key: str, *, down: bool) -> None:
    if os.name != "nt":
        raise RuntimeError("real_input_only_supported_on_windows")
    vk = _VK.get(key.upper())
    if vk is None:
        raise RuntimeError(f"unsupported_key:{key}")
    ctypes.windll.user32.keybd_event(vk, 0, 0 if down else 0x0002, 0)


def _mouse_move_relative(dx: int, dy: int) -> None:
    if os.name != "nt":
        raise RuntimeError("real_input_only_supported_on_windows")

    class MouseInput(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class InputUnion(ctypes.Union):
        _fields_ = [("mi", MouseInput)]

    class Input(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("union", InputUnion)]

    extra = ctypes.c_ulong(0)
    move = Input(type=0, union=InputUnion(mi=MouseInput(int(dx), int(dy), 0, 0x0001, 0, ctypes.pointer(extra))))
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(move), ctypes.sizeof(Input))
    if sent != 1:
        raise OSError("SendInput relative mouse move failed")


def _mouse_move(dx: int, dy: int) -> None:
    _mouse_move_relative(dx, dy)


def _file_sha256(path: str | None) -> str | None:
    if not path:
        return None
    target = Path(path)
    if not target.is_file():
        return None
    import hashlib

    digest = hashlib.sha256()
    with target.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _last_frame_from_actions(recent_actions: list[dict[str, object]]) -> str | None:
    for action in reversed(recent_actions):
        for key in ("after_image", "before_image"):
            value = action.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _action_key(action: dict[str, object]) -> str:
    action_type = str(action.get("action_type") or action.get("planned_action") or "")
    keys = action.get("keys")
    if action_type in {"key_hold", "key_press", "hotkey"} and isinstance(keys, list) and keys:
        return f"{action_type}:{'+'.join(str(key).upper() for key in keys)}"
    if action_type in {"mouse_move_relative", "mouse_move", "mouse_move_small"}:
        return "mouse_move_relative"
    return action_type


def _agent_step_index(recent_actions: list[dict[str, object]]) -> int:
    return sum(1 for action in recent_actions if str(action.get("action_id") or "").startswith("game_agent_")) + 1


def _last_mouse_dx(recent_actions: list[dict[str, object]]) -> int:
    for action in reversed(recent_actions):
        if str(action.get("action_type") or "") in {"mouse_move_relative", "mouse_move", "mouse_move_small"}:
            return int(action.get("mouse_dx") or 0)
    return 0


def _stuck_after(stuck_before: float, verify: dict[str, object]) -> float:
    if verify.get("changed") is True:
        return round(max(0.0, stuck_before - 0.35 - float(verify.get("visual_diff_score") or 0.0)), 4)
    return round(min(1.0, stuck_before + 0.1), 4)
