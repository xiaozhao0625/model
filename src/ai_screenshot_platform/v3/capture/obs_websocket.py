from __future__ import annotations

import base64
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat


@dataclass
class ObsConfig:
    host: str = "127.0.0.1"
    port: int = 4455
    password: str = ""
    scene_name: str | None = None
    source_name: str | None = None
    screenshot_target: str = "source"
    image_format: str = "png"
    image_quality: int = 90


def config_from_payload(payload: dict[str, Any] | None = None) -> ObsConfig:
    payload = payload or {}
    password = str(payload.get("obs_password") or os.environ.get("APP_SHOT_OBS_PASSWORD") or "")
    return ObsConfig(
        host=str(payload.get("obs_host") or os.environ.get("APP_SHOT_OBS_HOST") or "127.0.0.1"),
        port=int(payload.get("obs_port") or os.environ.get("APP_SHOT_OBS_PORT") or 4455),
        password=password,
        scene_name=_optional_str(payload.get("obs_scene_name") or os.environ.get("APP_SHOT_OBS_SCENE")),
        source_name=_optional_str(payload.get("obs_source_name") or os.environ.get("APP_SHOT_OBS_SOURCE")),
        screenshot_target=str(payload.get("screenshot_target") or "source"),
        image_format=str(payload.get("image_format") or "png").lower(),
        image_quality=int(payload.get("image_quality") or 90),
    )


def obs_status(config: ObsConfig | None = None) -> dict[str, Any]:
    config = config or config_from_payload()
    try:
        client = _connect(config)
        version = _to_dict(client.get_version())
        scenes_payload = _to_dict(client.get_scene_list())
        return {
            "obs_available": True,
            "connected": True,
            "host": config.host,
            "port": config.port,
            "version": version.get("obs_version") or version.get("obsVersion") or version.get("obs_web_socket_version"),
            "current_scene": _current_scene_name(scenes_payload),
            "error": None,
        }
    except Exception as exc:
        return {
            "obs_available": False,
            "connected": False,
            "host": config.host,
            "port": config.port,
            "version": None,
            "current_scene": None,
            "error": _friendly_error(exc),
        }


def list_scenes(config: ObsConfig | None = None) -> dict[str, Any]:
    config = config or config_from_payload()
    try:
        payload = _to_dict(_connect(config).get_scene_list())
        scenes = payload.get("scenes") or []
        return {
            "connected": True,
            "current_scene": _current_scene_name(payload),
            "scenes": [_scene_name(scene) for scene in scenes if _scene_name(scene)],
            "error": None,
        }
    except Exception as exc:
        return {"connected": False, "current_scene": None, "scenes": [], "error": _friendly_error(exc)}


def list_sources(config: ObsConfig | None = None, scene_name: str | None = None) -> dict[str, Any]:
    config = config or config_from_payload()
    try:
        client = _connect(config)
        scene = scene_name or config.scene_name or _current_scene_name(_to_dict(client.get_scene_list()))
        if not scene:
            return {"connected": True, "scene_name": None, "sources": [], "error": "未找到当前 OBS 场景。"}
        payload = _to_dict(client.get_scene_item_list(scene))
        items = payload.get("scene_items") or payload.get("sceneItems") or []
        sources = []
        for item in items:
            row = _to_dict(item)
            name = row.get("source_name") or row.get("sourceName")
            if name:
                sources.append(str(name))
        return {"connected": True, "scene_name": scene, "sources": sources, "error": None}
    except Exception as exc:
        return {"connected": False, "scene_name": scene_name or config.scene_name, "sources": [], "error": _friendly_error(exc)}


def take_obs_screenshot(config: ObsConfig, output_dir: str | Path, frame_index: int = 1) -> dict[str, Any]:
    client = _connect(config)
    scene_payload = _to_dict(client.get_scene_list())
    current_scene = _current_scene_name(scene_payload)
    source_name = config.source_name
    if not source_name and config.screenshot_target == "scene":
        source_name = config.scene_name or current_scene
    if not source_name:
        sources = list_sources(config, config.scene_name or current_scene)
        source_name = (sources.get("sources") or [None])[0]
    if not source_name:
        raise RuntimeError("未找到 OBS 来源，请确认 OBS 中已经添加窗口采集、游戏采集或显示器采集来源。")

    image_format = "jpg" if config.image_format in {"jpg", "jpeg"} else "png"
    payload = _to_dict(
        client.get_source_screenshot(
            source_name,
            image_format,
            None,
            None,
            config.image_quality,
        )
    )
    data_url = str(payload.get("image_data") or payload.get("imageData") or "")
    image_bytes = _decode_image_data(data_url)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    safe_source = re.sub(r"[^0-9A-Za-z._-]+", "_", source_name).strip("_") or "source"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    frame_path = output / f"frame_{timestamp}_{frame_index:06d}_obs_websocket_{safe_source}.{image_format}"
    frame_path.write_bytes(image_bytes)
    width, height, black_screen = _inspect_image(frame_path)
    return {
        "ok": True,
        "image_path": str(frame_path),
        "width": width,
        "height": height,
        "source_mode": "obs_websocket",
        "obs_scene_name": config.scene_name or current_scene,
        "obs_source_name": source_name,
        "black_screen_detected": black_screen,
        "message": "已获取截图，但画面可能是黑屏，请检查 OBS 来源是否正确捕获游戏。" if black_screen else "OBS WebSocket 测试截图成功。",
    }


def _connect(config: ObsConfig):
    try:
        import obsws_python  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on optional local package
        raise RuntimeError("未安装 obsws-python，无法连接 OBS WebSocket。") from exc
    return obsws_python.ReqClient(host=config.host, port=config.port, password=config.password, timeout=3)


def _decode_image_data(data: str) -> bytes:
    if "," in data:
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


def _inspect_image(path: Path) -> tuple[int, int, bool]:
    with Image.open(path) as image:
        width, height = image.size
        stat = ImageStat.Stat(image.convert("L"))
        mean = float(stat.mean[0]) if stat.mean else 0.0
        extrema = image.convert("L").getextrema()
    return width, height, bool(mean < 5.0 and extrema[1] < 20)


def _scene_name(scene: Any) -> str | None:
    row = _to_dict(scene)
    value = row.get("scene_name") or row.get("sceneName")
    return str(value) if value else None


def _current_scene_name(payload: dict[str, Any]) -> str | None:
    value = payload.get("current_program_scene_name") or payload.get("currentProgramSceneName")
    return str(value) if value else None


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "attrs") and isinstance(value.attrs(), dict):
        return value.attrs()
    if hasattr(value, "datain"):
        data = getattr(value, "datain")
        if isinstance(data, dict):
            return data
    return {key: getattr(value, key) for key in dir(value) if not key.startswith("_") and not callable(getattr(value, key))}


def _friendly_error(exc: Exception) -> str:
    text = str(exc) or exc.__class__.__name__
    if "Connection" in text or "refused" in text or "timed out" in text:
        return "未连接 OBS WebSocket。请打开 OBS，在工具或设置中启用 WebSocket 服务器，然后重试。"
    return text


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
