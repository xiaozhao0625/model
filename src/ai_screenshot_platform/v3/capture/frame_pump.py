from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import ImageGrab

from ai_screenshot_platform.v3.capture.obs_websocket import ObsConfig, take_obs_screenshot


def run_frame_pump(
    output_dir: str | Path,
    heartbeat_path: str | Path,
    stop_file: str | Path,
    fps: float = 1.0,
    window_title: str | None = None,
    full_screen: bool = True,
    source_mode: str = "screen",
    obs_host: str = "127.0.0.1",
    obs_port: int = 4455,
    obs_password: str = "",
    obs_scene_name: str | None = None,
    obs_source_name: str | None = None,
    screenshot_target: str = "source",
    image_format: str = "png",
    image_quality: int = 90,
    status_path: str | Path | None = None,
) -> int:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    heartbeat = Path(heartbeat_path)
    stop = Path(stop_file)
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    stop.parent.mkdir(parents=True, exist_ok=True)
    interval = 1.0 / max(0.2, fps)
    frame_index = 0
    mode = source_mode or ("window" if window_title else "screen")
    status = Path(status_path) if status_path else heartbeat.with_name("frame_pump_status.json")
    obs_config = ObsConfig(
        host=obs_host,
        port=obs_port,
        password=obs_password,
        scene_name=obs_scene_name,
        source_name=obs_source_name,
        screenshot_target=screenshot_target,
        image_format=image_format,
        image_quality=image_quality,
    )

    while not stop.exists():
        started = time.monotonic()
        try:
            frame_index += 1
            if mode == "obs_websocket":
                shot = take_obs_screenshot(obs_config, output, frame_index=frame_index)
                frame_path = Path(str(shot["image_path"]))
                obs_connected = True
            else:
                bbox = _window_bbox(window_title) if mode == "window" or window_title else None
                image = ImageGrab.grab(bbox=bbox) if bbox else ImageGrab.grab(all_screens=full_screen)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                frame_path = output / f"frame_{timestamp}_{frame_index:06d}_{mode}.png"
                image.save(frame_path)
                shot = {
                    "image_path": str(frame_path),
                    "width": image.width,
                    "height": image.height,
                    "black_screen_detected": False,
                }
                obs_connected = False
            payload = {
                "status": "running",
                "running": True,
                "timestamp": _utc_now(),
                "frame_path": str(frame_path),
                "last_frame_path": str(frame_path),
                "last_frame_at": _utc_now(),
                "frame_index": frame_index,
                "frame_count": frame_index,
                "fps": fps,
                "mode": mode,
                "source_mode": mode,
                "obs_connected": obs_connected,
                "obs_scene_name": obs_scene_name,
                "obs_source_name": obs_source_name,
                "output_dir": str(output),
                "last_error": None,
                "capture_reason": "periodic",
                "action_id": None,
                "ui_state_hint": "main_view",
                "width": shot.get("width"),
                "height": shot.get("height"),
                "black_screen_detected": shot.get("black_screen_detected", False),
            }
            _write_json(frame_path.with_suffix(".json"), payload)
            _write_json(heartbeat, payload)
            _write_json(status, payload)
        except Exception as exc:
            payload = {
                "status": "error",
                "running": True,
                "timestamp": _utc_now(),
                "frame_index": frame_index,
                "frame_count": frame_index,
                "fps": fps,
                "mode": mode,
                "source_mode": mode,
                "obs_connected": False,
                "obs_scene_name": obs_scene_name,
                "obs_source_name": obs_source_name,
                "output_dir": str(output),
                "last_error": str(exc),
                "error": str(exc),
            }
            _write_json(heartbeat, payload)
            _write_json(status, payload)
        elapsed = time.monotonic() - started
        time.sleep(max(0.01, interval - elapsed))

    payload = {
        "status": "stopped",
        "running": False,
        "timestamp": _utc_now(),
        "frame_index": frame_index,
        "frame_count": frame_index,
        "fps": fps,
        "mode": mode,
        "source_mode": mode,
        "obs_connected": False,
        "obs_scene_name": obs_scene_name,
        "obs_source_name": obs_source_name,
        "output_dir": str(output),
        "last_error": None,
    }
    _write_json(heartbeat, payload)
    _write_json(status, payload)
    return 0


def _window_bbox(pattern: str | None) -> tuple[int, int, int, int] | None:
    if not pattern or os.name != "nt":
        return None
    user32 = ctypes.windll.user32
    regex = re.compile(pattern, re.IGNORECASE)
    found: list[int] = []

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if buffer.value and regex.search(buffer.value):
            found.append(hwnd)
            return False
        return True

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(callback)
    user32.EnumWindows(enum_proc, 0)
    if not found:
        raise RuntimeError(f"target window not found: {pattern}")
    rect = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(found[0], ctypes.byref(rect)):
        raise RuntimeError("GetWindowRect failed")
    return rect.left, rect.top, rect.right, rect.bottom


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--heartbeat-path", required=True)
    parser.add_argument("--stop-file", required=True)
    parser.add_argument("--fps", type=float, default=1.0)
    parser.add_argument("--window-title")
    parser.add_argument("--full-screen", action="store_true")
    parser.add_argument("--source-mode", default="screen")
    parser.add_argument("--obs-host", default="127.0.0.1")
    parser.add_argument("--obs-port", type=int, default=4455)
    parser.add_argument("--obs-password", default=os.environ.get("APP_SHOT_OBS_PASSWORD", ""))
    parser.add_argument("--obs-scene-name")
    parser.add_argument("--obs-source-name")
    parser.add_argument("--screenshot-target", default="source")
    parser.add_argument("--image-format", default="png")
    parser.add_argument("--image-quality", type=int, default=90)
    parser.add_argument("--status-path")
    args = parser.parse_args()
    return run_frame_pump(
        output_dir=args.output_dir,
        heartbeat_path=args.heartbeat_path,
        stop_file=args.stop_file,
        fps=args.fps,
        window_title=args.window_title,
        full_screen=args.full_screen,
        source_mode=args.source_mode,
        obs_host=args.obs_host,
        obs_port=args.obs_port,
        obs_password=args.obs_password,
        obs_scene_name=args.obs_scene_name,
        obs_source_name=args.obs_source_name,
        screenshot_target=args.screenshot_target,
        image_format=args.image_format,
        image_quality=args.image_quality,
        status_path=args.status_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
