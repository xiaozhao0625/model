from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image, ImageFilter, ImageStat

from ai_screenshot_platform.v3.schemas import V3TaskConfig


UI_KEYWORDS = {
    "inventory": ("inventory", "backpack", "bag", "item", "items", "背包", "道具"),
    "warehouse": ("warehouse", "stash", "storage", "仓库"),
    "map": ("map", "地图"),
    "equipment": ("equipment", "weapon", "gear", "loadout", "装备", "武器"),
    "settings": ("setting", "settings", "options", "设置"),
    "mission": ("mission", "quest", "task", "任务"),
}

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
    "验证码": "captcha",
    "充值": "payment",
    "支付": "payment",
    "商城": "shop",
    "购买": "shop",
    "匹配": "matchmaking",
    "排位": "ranked",
    "聊天": "chat",
    "发送": "chat",
    "账号": "account",
}


class GameVisionObserver:
    def observe(
        self,
        *,
        config: V3TaskConfig,
        current_frame: str | None,
        previous_frame: str | None = None,
        recent_actions: list[dict[str, object]] | None = None,
        ocr_text: str = "",
        last_action_effect: str | None = None,
    ) -> dict[str, object]:
        recent_actions = recent_actions or []
        previous_frame = previous_frame or _last_frame_from_actions(recent_actions)
        frame_features = compare_frames(previous_frame, current_frame)
        text_features = analyze_text(ocr_text)
        near_duplicate_ratio, repeated_frame_count = _recent_repeat_stats(recent_actions)
        accepted_unique_delta_recent = sum(int(action.get("accepted_unique_delta") or 0) for action in recent_actions[-5:])
        possible_wall = bool(
            current_frame
            and frame_features["center_edge_density"] >= 0.18
            and frame_features["center_diff_score"] < 0.07
            and _recent_forward_count(recent_actions) > 0
        )
        stuck_score = _stuck_score(
            visual_diff=float(frame_features["visual_diff_score"]),
            center_diff=float(frame_features["center_diff_score"]),
            near_duplicate_ratio=near_duplicate_ratio,
            repeated_frame_count=repeated_frame_count,
            accepted_unique_delta_recent=accepted_unique_delta_recent,
            possible_wall=possible_wall,
        )
        state = classify_context(
            config=config,
            ocr_text=ocr_text,
            text_features=text_features,
            possible_wall_ahead=possible_wall,
            stuck_score=stuck_score,
            near_duplicate_ratio=near_duplicate_ratio,
        )
        risk_flags = sorted(set(text_features["risk_flags"]))
        suggested = _suggested_context(state, stuck_score, possible_wall, near_duplicate_ratio, risk_flags)
        return {
            "state": state,
            "has_text": bool(ocr_text.strip()),
            "ocr_text": ocr_text,
            "ocr_text_density": text_features["ocr_text_density"],
            "text_box_count": text_features["text_box_count"],
            "text_area_ratio": text_features["text_area_ratio"],
            "chinese_text_ratio": text_features["chinese_text_ratio"],
            "ui_text_keywords": text_features["ui_text_keywords"],
            "risk_flags": risk_flags,
            "visual_summary": "latest_frame_available" if current_frame else "no_frame",
            "last_action_effect": last_action_effect or "unknown",
            "near_duplicate_ratio": near_duplicate_ratio,
            "repeated_frame_count": repeated_frame_count,
            "accepted_unique_delta_recent": accepted_unique_delta_recent,
            "possible_wall_ahead": possible_wall,
            "stuck_score": stuck_score,
            "suggested_context": suggested,
            **frame_features,
        }


def compare_frames(previous_frame: str | None, current_frame: str | None) -> dict[str, object]:
    current = _load_image(current_frame)
    previous = _load_image(previous_frame)
    current_edge_density = _edge_density(current) if current is not None else 0.0
    if current is None or previous is None:
        return {
            "visual_diff_score": 0.0,
            "histogram_diff_score": 0.0,
            "edge_diff_score": 0.0,
            "perceptual_hash_distance": 0,
            "center_diff_score": 0.0,
            "center_motion_score": 0.0,
            "center_edge_density": current_edge_density,
            "center_texture_change": 0.0,
            "center_brightness_change": 0.0,
            "ui_page_likelihood": 0.0,
            "map_page_likelihood": 0.0,
            "inventory_page_likelihood": 0.0,
        }

    resized_previous = _resize_gray(previous)
    resized_current = _resize_gray(current)
    center_previous = _center_crop(previous)
    center_current = _center_crop(current)
    center_previous_small = _resize_gray(center_previous, size=(64, 64))
    center_current_small = _resize_gray(center_current, size=(64, 64))
    visual_diff = _mean_abs_diff(resized_previous, resized_current)
    center_diff = _mean_abs_diff(center_previous_small, center_current_small)
    return {
        "visual_diff_score": round(visual_diff, 4),
        "histogram_diff_score": round(_histogram_diff(resized_previous, resized_current), 4),
        "edge_diff_score": round(_mean_abs_diff(_edges(resized_previous), _edges(resized_current)), 4),
        "perceptual_hash_distance": _hash_distance(_average_hash(resized_previous), _average_hash(resized_current)),
        "center_diff_score": round(center_diff, 4),
        "center_motion_score": round(center_diff, 4),
        "center_edge_density": round(_edge_density(center_current_small), 4),
        "center_texture_change": round(abs(_stddev(center_current_small) - _stddev(center_previous_small)) / 255.0, 4),
        "center_brightness_change": round(abs(_brightness(center_current_small) - _brightness(center_previous_small)) / 255.0, 4),
        "ui_page_likelihood": 0.0,
        "map_page_likelihood": 0.0,
        "inventory_page_likelihood": 0.0,
    }


def analyze_text(ocr_text: str) -> dict[str, object]:
    text = ocr_text or ""
    lowered = text.casefold()
    tokens = [part for part in text.replace("\n", " ").split(" ") if part.strip()]
    cjk_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    visible_count = sum(1 for char in text if not char.isspace())
    ui_hits: list[str] = []
    for label, words in UI_KEYWORDS.items():
        if any(word.casefold() in lowered for word in words):
            ui_hits.append(label)
    risk_flags = sorted({state for term, state in RISK_TERMS.items() if term.casefold() in lowered})
    text_box_count = max(len(tokens), len([line for line in text.splitlines() if line.strip()]))
    return {
        "ocr_text_density": round(min(1.0, visible_count / 800.0), 4),
        "text_box_count": text_box_count,
        "text_area_ratio": round(min(0.8, text_box_count * 0.012), 4),
        "chinese_text_ratio": round(cjk_count / visible_count, 4) if visible_count else 0.0,
        "ui_text_keywords": ui_hits,
        "risk_flags": risk_flags,
    }


def classify_context(
    *,
    config: V3TaskConfig,
    ocr_text: str,
    text_features: dict[str, object],
    possible_wall_ahead: bool,
    stuck_score: float,
    near_duplicate_ratio: float,
) -> str:
    risk_flags = text_features.get("risk_flags") or []
    if risk_flags:
        return "risk_page"
    ui_hits = set(text_features.get("ui_text_keywords") or [])
    if "inventory" in ui_hits:
        return "ui_inventory"
    if "warehouse" in ui_hits:
        return "ui_warehouse"
    if "map" in ui_hits:
        return "ui_map"
    if "equipment" in ui_hits:
        return "ui_equipment"
    if "settings" in ui_hits:
        return "ui_settings"
    if "mission" in ui_hits:
        return "ui_mission"
    if stuck_score >= 0.72:
        return "training_stuck" if _is_training_config(config) else "gameplay_no_change"
    if possible_wall_ahead:
        return "training_blocked_ahead" if _is_training_config(config) else "gameplay_no_change"
    if near_duplicate_ratio >= 0.7:
        return "unknown_repeated"
    if (text_features.get("text_area_ratio") or 0) >= 0.16 and ocr_text.strip():
        return "hud_with_text"
    if _is_training_config(config):
        return "training_open_area"
    if config.game_mode == "gameplay":
        return "gameplay_moving"
    return "unknown_safe" if ocr_text.strip() or config.app_type == "pc_game" else "unknown_repeated"


def _load_image(path: str | None) -> Image.Image | None:
    if not path:
        return None
    target = Path(path)
    if not target.is_file():
        return None
    try:
        return Image.open(target).convert("RGB")
    except Exception:
        return None


def _resize_gray(image: Image.Image, size: tuple[int, int] = (96, 96)) -> Image.Image:
    return image.convert("L").resize(size)


def _center_crop(image: Image.Image) -> Image.Image:
    width, height = image.size
    left = int(width * 0.3)
    top = int(height * 0.3)
    right = int(width * 0.7)
    bottom = int(height * 0.7)
    return image.crop((left, top, right, bottom))


def _mean_abs_diff(a: Image.Image, b: Image.Image) -> float:
    a_values = list(a.getdata())
    b_values = list(b.getdata())
    if not a_values or len(a_values) != len(b_values):
        return 0.0
    return mean(abs(int(x) - int(y)) for x, y in zip(a_values, b_values)) / 255.0


def _histogram_diff(a: Image.Image, b: Image.Image) -> float:
    hist_a = a.histogram()
    hist_b = b.histogram()
    total = max(1, sum(hist_a))
    return sum(abs(x - y) for x, y in zip(hist_a, hist_b)) / (2 * total)


def _edges(image: Image.Image) -> Image.Image:
    return image.filter(ImageFilter.FIND_EDGES)


def _edge_density(image: Image.Image) -> float:
    edges = _edges(image.convert("L"))
    pixels = list(edges.getdata())
    if not pixels:
        return 0.0
    return sum(1 for value in pixels if int(value) > 28) / len(pixels)


def _average_hash(image: Image.Image) -> int:
    tiny = image.convert("L").resize((8, 8))
    values = list(tiny.getdata())
    avg = sum(values) / len(values)
    result = 0
    for index, value in enumerate(values):
        if value >= avg:
            result |= 1 << index
    return result


def _hash_distance(a: int, b: int) -> int:
    return int((a ^ b).bit_count())


def _stddev(image: Image.Image) -> float:
    return float(ImageStat.Stat(image.convert("L")).stddev[0])


def _brightness(image: Image.Image) -> float:
    return float(ImageStat.Stat(image.convert("L")).mean[0])


def _recent_repeat_stats(recent_actions: list[dict[str, object]]) -> tuple[float, int]:
    candidates = recent_actions[-6:]
    if not candidates:
        return 0.0, 0
    repeated = 0
    for action in candidates:
        verify = action.get("verify")
        status = str(verify.get("status") if isinstance(verify, dict) else action.get("verify_status") or "")
        diff = float(action.get("visual_diff_score") or (verify.get("visual_diff_score") if isinstance(verify, dict) else 0.0) or 0.0)
        if status in {"no_visual_change", "stuck"} or diff < 0.08:
            repeated += 1
    return round(repeated / len(candidates), 4), repeated


def _recent_forward_count(recent_actions: list[dict[str, object]]) -> int:
    count = 0
    for action in recent_actions[-5:]:
        keys = [str(key).upper() for key in action.get("keys", [])] if isinstance(action.get("keys"), list) else []
        if action.get("action_type") == "key_hold" and "W" in keys:
            count += 1
    return count


def _stuck_score(
    *,
    visual_diff: float,
    center_diff: float,
    near_duplicate_ratio: float,
    repeated_frame_count: int,
    accepted_unique_delta_recent: int,
    possible_wall: bool,
) -> float:
    score = 0.0
    if visual_diff < 0.08:
        score += 0.25
    if center_diff < 0.05:
        score += 0.25
    score += min(0.25, near_duplicate_ratio * 0.25)
    if repeated_frame_count >= 3:
        score += 0.1
    if accepted_unique_delta_recent == 0:
        score += 0.08
    if possible_wall:
        score += 0.15
    return round(min(1.0, score), 4)


def _suggested_context(state: str, stuck_score: float, possible_wall: bool, near_duplicate_ratio: float, risk_flags: list[str]) -> str:
    if risk_flags:
        return "risk_page"
    if stuck_score >= 0.72:
        return "training_stuck"
    if possible_wall:
        return "training_blocked_ahead"
    if near_duplicate_ratio >= 0.7:
        return "unknown_repeated"
    return state


def _last_frame_from_actions(recent_actions: list[dict[str, object]]) -> str | None:
    for action in reversed(recent_actions):
        for key in ("after_image", "before_image"):
            value = action.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _is_training_config(config: V3TaskConfig) -> bool:
    return bool(config.allow_training_movement or config.allow_wasd or config.allow_mouse_look or config.game_mode == "gameplay")
