from __future__ import annotations

import ctypes
import os
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from ai_screenshot_platform.v3.action.input_gateway import load_input_gateway_readiness
from ai_screenshot_platform.v3.schemas import V3TaskConfig, utc_now


RISK_STATES = {"login", "shop", "payment", "matchmaking", "ranked", "chat", "account", "captcha", "uac", "secure_desktop"}
RISK_TERMS = {
    "login": "login",
    "password": "login",
    "captcha": "captcha",
    "verify": "captcha",
    "payment": "payment",
    "pay": "payment",
    "shop": "shop",
    "store": "shop",
    "ranked": "ranked",
    "matchmaking": "matchmaking",
    "chat": "chat",
    "account": "account",
    "登录": "login",
    "密码": "login",
    "验证码": "captcha",
    "支付": "payment",
    "充值": "payment",
    "商城": "shop",
    "购买": "shop",
    "排位": "ranked",
    "匹配": "matchmaking",
    "聊天": "chat",
    "账号": "account",
}


class GameAgentLoop:
    def __init__(
        self,
        *,
        allow_real_input: bool | None = None,
        readiness_loader: Callable[[], object] = load_input_gateway_readiness,
    ) -> None:
        self.allow_real_input = (
            os.environ.get("APP_SHOT_ALLOW_REAL_INPUT", "").strip() == "1"
            if allow_real_input is None
            else allow_real_input
        )
        self.readiness_loader = readiness_loader

    def observe(self, *, config: V3TaskConfig, before_image: str | None, ocr_text: str = "", last_action_effect: str | None = None) -> dict[str, object]:
        state = self.classify_state(ocr_text=ocr_text, config=config)
        return {
            "state": state,
            "has_text": bool(ocr_text.strip()),
            "ocr_text": ocr_text,
            "risk_flags": sorted({state} & RISK_STATES),
            "visual_summary": "latest_frame_available" if before_image else "no_frame",
            "last_action_effect": last_action_effect or "unknown",
        }

    def classify_state(self, *, ocr_text: str, config: V3TaskConfig) -> str:
        lowered = ocr_text.casefold()
        for term, state in RISK_TERMS.items():
            if term.casefold() in lowered:
                return state
        if any(term in lowered for term in ("inventory", "backpack", "bag", "仓库", "背包", "装备", "物品")):
            return "inventory"
        if any(term in lowered for term in ("map", "地图")):
            return "map"
        if any(term in lowered for term in ("setting", "settings", "设置")):
            return "settings"
        if any(term in lowered for term in ("mission", "quest", "任务")):
            return "mission"
        if any(term in lowered for term in ("dialog", "对话")):
            return "dialog"
        if config.game_mode == "gameplay" or config.allow_training_movement or config.allow_wasd or config.allow_mouse_look:
            return "training"
        if ocr_text.strip():
            return "main_menu"
        return "unknown"

    def plan(self, *, config: V3TaskConfig, observation: dict[str, object], before_image: str | None) -> dict[str, object]:
        state = str(observation.get("state") or "unknown")
        if not config.enable_game_agent and not config.enable_game_explorer:
            return self._blocked_plan("wait", "game_agent_disabled", state)
        if not (config.safe_scene_confirmed or config.safe_game_scene_confirmed):
            return self._blocked_plan("wait", "safe_scene_not_confirmed", state)
        if state in RISK_STATES:
            return self._blocked_plan("wait", f"unsafe_state_{state}", state)
        if not self._has_any_capability(config):
            return self._blocked_plan("wait", "no_action_capability_enabled", state)
        if not before_image:
            disabled_probe = self._real_input_disabled_probe_plan(config, state)
            if disabled_probe is not None:
                return disabled_probe
            return self._blocked_plan("wait", "frame_pump_no_frame", state)
        if state in {"inventory", "warehouse", "equipment", "weapon", "skill", "mission"} and config.allow_inventory_map_explore and config.allow_hotkeys:
            return {"action_type": "key_press", "planned_action": "key_press", "keys": ["Tab"], "duration_ms": 80, "reason": f"{state} 页面低风险切换面板", "observed_state": state}
        if state == "map" and config.allow_inventory_map_explore and config.allow_mouse_look:
            return {"action_type": "mouse_move_small", "planned_action": "mouse_move_small", "mouse_dx": 80, "mouse_dy": 0, "duration_ms": 120, "reason": "地图页面小幅拖动以产生新视角", "observed_state": state}
        if state in {"training", "gameplay"}:
            if (config.allow_wasd or config.allow_training_movement) and config.allow_hotkeys:
                return {"action_type": "key_hold", "planned_action": "key_hold", "keys": ["W"], "duration_ms": 800, "reason": "训练场移动以产生新视角", "observed_state": state}
            if config.allow_mouse_look:
                return {"action_type": "mouse_move_small", "planned_action": "mouse_move_small", "mouse_dx": 60, "mouse_dy": 0, "duration_ms": 120, "reason": "训练场小幅改变视角", "observed_state": state}
        if state in {"main_menu", "settings", "dialog"} and config.allow_back_close and config.allow_hotkeys:
            return {"action_type": "key_press", "planned_action": "key_press", "keys": ["Esc"], "duration_ms": 80, "reason": "低风险返回或关闭弹窗", "observed_state": state}
        if config.allow_hotkeys:
            return {"action_type": "key_press", "planned_action": "key_press", "keys": ["Tab"], "duration_ms": 80, "reason": "未知状态下低风险切换面板", "observed_state": state}
        return self._blocked_plan("wait", "no_safe_plan_for_state", state)

    def act(self, plan: dict[str, object]) -> dict[str, object]:
        blocked_reason = plan.get("blocked_reason")
        if blocked_reason:
            return {"executed": False, "reason": blocked_reason, "status": "blocked"}
        if not self.allow_real_input:
            return {"executed": False, "reason": "real_input_disabled", "status": "blocked"}
        readiness = self.readiness_loader()
        if not getattr(readiness, "input_gateway_ready", False):
            blockers = getattr(readiness, "blockers", []) or []
            return {"executed": False, "reason": "input_gateway_not_ready", "status": "blocked", "blockers": blockers}
        action_type = str(plan.get("action_type") or "wait")
        try:
            if action_type == "key_hold":
                _key_hold([str(key) for key in plan.get("keys", [])], int(plan.get("duration_ms") or 500))
            elif action_type == "key_press":
                _key_press([str(key) for key in plan.get("keys", [])])
            elif action_type == "mouse_move_small":
                _mouse_move(int(plan.get("mouse_dx") or 0), int(plan.get("mouse_dy") or 0))
            else:
                return {"executed": False, "reason": f"unsupported_action:{action_type}", "status": "blocked"}
        except Exception as exc:  # pragma: no cover - depends on interactive desktop.
            return {"executed": False, "reason": f"input_execution_failed:{exc}", "status": "error"}
        return {"executed": True, "reason": "real_input_executed", "status": "executed"}

    def verify(self, *, before_image: str | None, after_image: str | None) -> dict[str, object]:
        before_sha = _file_sha256(before_image)
        after_sha = _file_sha256(after_image)
        changed = bool(before_sha and after_sha and before_sha != after_sha)
        return {
            "before_sha256": before_sha,
            "after_sha256": after_sha,
            "changed": changed,
            "status": "changed" if changed else "no_visual_change",
            "visual_diff_score": 0.35 if changed else 0.0,
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
    ) -> dict[str, object]:
        observation = self.observe(config=config, before_image=before_image, ocr_text=ocr_text, last_action_effect=last_action_effect)
        plan = self.plan(config=config, observation=observation, before_image=before_image)
        result = self.act(plan)
        if latest_image_fn is not None:
            time.sleep(max(0.1, action_interval_ms / 1000))
            after_image = latest_image_fn()
        verify = self.verify(before_image=before_image, after_image=after_image)
        blocked_reason = plan.get("blocked_reason") or (None if result.get("executed") else result.get("reason"))
        return {
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
            "executed": bool(result.get("executed")),
            "blocked_reason": str(blocked_reason) if blocked_reason else None,
            "before_image": before_image,
            "after_image": after_image,
            "visual_diff_score": verify["visual_diff_score"],
            "verify": verify,
            "result": result,
            "created_at": utc_now(),
        }

    def _blocked_plan(self, action_type: str, reason: str, state: str) -> dict[str, object]:
        return {
            "action_type": action_type,
            "planned_action": action_type,
            "reason": reason,
            "blocked_reason": reason,
            "observed_state": state,
        }

    def _real_input_disabled_probe_plan(self, config: V3TaskConfig, state: str) -> dict[str, object] | None:
        if self.allow_real_input:
            return None
        if config.allow_wasd or config.allow_training_movement:
            return {"action_type": "key_hold", "planned_action": "key_hold", "keys": ["W"], "duration_ms": 500, "reason": "real_input_disabled", "observed_state": state}
        if config.allow_mouse_look:
            return {"action_type": "mouse_move_small", "planned_action": "mouse_move_small", "mouse_dx": 40, "mouse_dy": 0, "duration_ms": 120, "reason": "real_input_disabled", "observed_state": state}
        if config.allow_hotkeys:
            return {"action_type": "key_press", "planned_action": "key_press", "keys": ["Tab"], "duration_ms": 80, "reason": "real_input_disabled", "observed_state": state}
        if config.allow_ui_click or config.enable_auto_click:
            return {"action_type": "ui_click", "planned_action": "ui_click", "duration_ms": 80, "reason": "real_input_disabled", "observed_state": state}
        return None

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


def _mouse_move(dx: int, dy: int) -> None:
    if os.name != "nt":
        raise RuntimeError("real_input_only_supported_on_windows")
    ctypes.windll.user32.mouse_event(0x0001, dx, dy, 0, 0)


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
