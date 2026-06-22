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


def run_frame_pump(
    output_dir: str | Path,
    heartbeat_path: str | Path,
    stop_file: str | Path,
    fps: float = 1.0,
    window_title: str | None = None,
    full_screen: bool = True,
) -> int:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    heartbeat = Path(heartbeat_path)
    stop = Path(stop_file)
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    stop.parent.mkdir(parents=True, exist_ok=True)
    interval = 1.0 / max(0.2, fps)
    frame_index = 0
    mode = "window" if window_title else "fullscreen"

    while not stop.exists():
        started = time.monotonic()
        try:
            bbox = _window_bbox(window_title) if window_title else None
            image = ImageGrab.grab(bbox=bbox) if bbox else ImageGrab.grab(all_screens=full_screen)
            frame_index += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            frame_path = output / f"frame_{timestamp}_{frame_index:06d}.png"
            image.save(frame_path)
            payload = {
                "status": "running",
                "timestamp": _utc_now(),
                "frame_path": str(frame_path),
                "frame_index": frame_index,
                "fps": fps,
                "mode": mode,
                "capture_reason": "periodic",
                "action_id": None,
                "ui_state_hint": "main_view",
            }
            _write_json(frame_path.with_suffix(".json"), payload)
            _write_json(heartbeat, payload)
        except Exception as exc:
            _write_json(
                heartbeat,
                {
                    "status": "error",
                    "timestamp": _utc_now(),
                    "frame_index": frame_index,
                    "fps": fps,
                    "mode": mode,
                    "error": str(exc),
                },
            )
        elapsed = time.monotonic() - started
        time.sleep(max(0.01, interval - elapsed))

    _write_json(
        heartbeat,
        {
            "status": "stopped",
            "timestamp": _utc_now(),
            "frame_index": frame_index,
            "fps": fps,
            "mode": mode,
        },
    )
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
    args = parser.parse_args()
    return run_frame_pump(
        output_dir=args.output_dir,
        heartbeat_path=args.heartbeat_path,
        stop_file=args.stop_file,
        fps=args.fps,
        window_title=args.window_title,
        full_screen=args.full_screen,
    )


if __name__ == "__main__":
    raise SystemExit(main())
