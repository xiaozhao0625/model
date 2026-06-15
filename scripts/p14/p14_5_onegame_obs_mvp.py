from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import time
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PROFILE = Path("configs/game_profiles/onegame_mvp.example.json")
DEFAULT_QUALITY = Path("configs/quality/frame_quality_gate.game.json")
DEFAULT_BEHAVIOR = Path("configs/game_behavior_packs/basic_explore_v1.json")
SAFE_BLOCKED_ACTIONS = {"login", "chat", "purchase", "matchmaking", "ranked", "captcha", "payment"}


@dataclass(frozen=True)
class FrameQuality:
    quality_status: str
    dedup_status: str
    reject_reason: str | None
    content_hash: str
    phash: str
    dhash: str
    brightness_mean: float
    brightness_std: float
    laplacian_var: float
    black_ratio: float
    white_ratio: float
    edge_density: float
    entropy: float
    frame_diff: float
    width: int
    height: int
    duplicate_of: str | None = None


class OneGameQualityGate:
    def __init__(self, policy: dict[str, Any]) -> None:
        self.policy = policy
        self._seen_hashes: dict[str, str] = {}
        self._seen_dhashes: dict[str, str] = {}
        self._previous_gray: list[int] | None = None
        self._previous_id: str | None = None

    def evaluate(self, image_id: str, path: Path) -> FrameQuality:
        pixels = read_png_pixels(path)
        gray = pixels.gray
        content_hash = sha256(path)
        dhash = difference_hash(gray, pixels.width, pixels.height)
        phash = average_hash(gray, pixels.width, pixels.height)
        brightness_mean = sum(gray) / max(len(gray), 1)
        brightness_std = stddev(gray, brightness_mean)
        black_ratio = sum(1 for value in gray if value <= 10) / max(len(gray), 1)
        white_ratio = sum(1 for value in gray if value >= 245) / max(len(gray), 1)
        edge_density = mean_adjacent_diff(gray, pixels.width, pixels.height)
        laplacian_var = laplacian_variance(gray, pixels.width, pixels.height)
        entropy = grayscale_entropy(gray)
        frame_diff = 999.0 if self._previous_gray is None else mean_abs_diff(gray, self._previous_gray)

        reject_reason: str | None = None
        duplicate_of: str | None = None
        if pixels.width < int(self.policy["min_width"]) or pixels.height < int(self.policy["min_height"]):
            reject_reason = "low_resolution"
        elif black_ratio >= float(self.policy["black_ratio_threshold"]) and brightness_mean <= float(self.policy["black_brightness_max"]):
            reject_reason = "black_screen"
        elif white_ratio >= float(self.policy["white_ratio_threshold"]) and brightness_mean >= float(self.policy["white_brightness_min"]):
            reject_reason = "white_screen"
        elif laplacian_var <= float(self.policy["low_detail_laplacian_var_max"]) and entropy <= float(self.policy["low_entropy_max"]):
            reject_reason = "low_quality"
        elif content_hash in self._seen_hashes:
            reject_reason = "duplicate"
            duplicate_of = self._seen_hashes[content_hash]
        else:
            for existing_id, existing_hash in self._seen_dhashes.items():
                if (
                    hamming_hex(dhash, existing_hash) <= int(self.policy["duplicate_dhash_max_distance"])
                    and frame_diff <= float(self.policy["stuck_frame_diff_max"])
                ):
                    reject_reason = "duplicate"
                    duplicate_of = existing_id
                    break
        if reject_reason is None and frame_diff <= float(self.policy["stuck_frame_diff_max"]):
            reject_reason = "stuck_frame"
            duplicate_of = self._previous_id

        if reject_reason is None:
            self._seen_hashes[content_hash] = image_id
            self._seen_dhashes[image_id] = dhash
            self._previous_gray = gray
            self._previous_id = image_id

        quality_status = "accepted" if reject_reason is None else ("duplicate" if reject_reason in {"duplicate", "stuck_frame"} else "rejected")
        dedup_status = "duplicate" if reject_reason in {"duplicate", "stuck_frame"} else "unique"
        return FrameQuality(
            quality_status=quality_status,
            dedup_status=dedup_status,
            reject_reason=reject_reason,
            content_hash=content_hash,
            phash=phash,
            dhash=dhash,
            brightness_mean=round(brightness_mean, 3),
            brightness_std=round(brightness_std, 3),
            laplacian_var=round(laplacian_var, 3),
            black_ratio=round(black_ratio, 6),
            white_ratio=round(white_ratio, 6),
            edge_density=round(edge_density, 3),
            entropy=round(entropy, 3),
            frame_diff=round(frame_diff, 3),
            width=pixels.width,
            height=pixels.height,
            duplicate_of=duplicate_of,
        )


@dataclass(frozen=True)
class PngPixels:
    width: int
    height: int
    gray: list[int]


def main() -> int:
    args = parse_args()
    profile = read_json(args.profile)
    quality_policy = read_json(args.quality_policy)
    behavior_pack = read_json(args.behavior_pack)
    target_total = int(args.target_total or profile.get("target_total", 100))
    if target_total < 1 or target_total > 300:
        raise ValueError("OneGame MVP target_total must be between 1 and 300")
    if args.mode == "plan":
        run_id = args.run_id or default_run_id(args.mode)
        run_dir = Path(args.output_root) / run_id
        result = write_blocked_outputs(
            run_dir,
            run_id,
            profile,
            args.mode,
            now_iso(),
            "blocked_by_no_user_prepared_game_profiles",
        )
        result["message"] = "Please open one PC game on W1, enter one safe scene, and verify OBS preview before real capture."
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    if args.mode == "real" and not args.user_ready:
        result = blocked_result(args, profile, "blocked_by_user_not_ready")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    run_id = args.run_id or default_run_id(args.mode)
    run_dir = Path(args.output_root) / run_id
    create_run_dirs(run_dir)
    started_at = now_iso()
    action_log = write_behavior_actions(run_dir, behavior_pack, execute_real=args.execute_behavior)
    try:
        obs_result = verify_obs(profile, dry_run=args.mode == "dry-run")
        frame_paths = capture_frames(args, profile, run_dir, target_total)
        if args.inject_quality_fixtures:
            frame_paths.extend(inject_quality_fixtures(run_dir / "raw", frame_paths))
        records, summary_counts = evaluate_frames(
            frame_paths=frame_paths,
            run_dir=run_dir,
            run_id=run_id,
            profile=profile,
            quality_policy=quality_policy,
            mode=args.mode,
            obs_result=obs_result,
        )
        write_outputs(
            run_dir=run_dir,
            run_id=run_id,
            profile=profile,
            mode=args.mode,
            started_at=started_at,
            records=records,
            summary_counts=summary_counts,
            target_total=target_total,
            action_log=action_log,
            obs_result=obs_result,
        )
        status = "capture_completed" if summary_counts["valid_total"] >= min(60, max(1, int(target_total * 0.6))) else "failed_low_yield"
        result = {
            "status": status,
            "run_id": run_id,
            "mode": args.mode,
            "run_dir": str(run_dir),
            "attempted": summary_counts["attempted"],
            "valid_total": summary_counts["valid_total"],
            "duplicate_count": summary_counts["duplicate_count"],
            "black_screen_count": summary_counts["black_screen_count"],
            "low_quality_count": summary_counts["low_quality_count"],
            "rejected_count": summary_counts["rejected_count"],
            "test_source": args.mode == "dry-run",
            "production_capture": args.mode == "real",
            "online_inference": False,
            "model_action_control": False,
            "automatic_upload": False,
            "automatic_cleanup": False,
            "obs": obs_result,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if status == "capture_completed" else 1
    except Exception as exc:
        result = write_blocked_outputs(run_dir, run_id, profile, args.mode, started_at, str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P14.5 OneGame MVP OBS frame capture and quality gate.")
    parser.add_argument("--mode", choices=["plan", "dry-run", "real"], default="plan")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--quality-policy", default=str(DEFAULT_QUALITY))
    parser.add_argument("--behavior-pack", default=str(DEFAULT_BEHAVIOR))
    parser.add_argument("--output-root", default=r"D:\work\runs")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--target-total", type=int, default=0)
    parser.add_argument("--ffmpeg-path", default="")
    parser.add_argument("--user-ready", action="store_true")
    parser.add_argument("--execute-behavior", action="store_true")
    parser.add_argument("--inject-quality-fixtures", action="store_true")
    return parser.parse_args()


def blocked_result(args: argparse.Namespace, profile: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "profile": profile.get("game_id"),
        "requires_user_ready": bool(profile.get("requires_user_ready", True)),
        "message": "Please open the game on W1, enter one safe scene, verify OBS preview, then rerun with --user-ready.",
        "online_inference": False,
        "model_action_control": False,
    }


def verify_obs(profile: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run_test_source",
            "websocket_connected": False,
            "scene_detected": False,
            "source_detected": False,
            "test_source": True,
            "production_capture": False,
        }
    try:
        from obsws_python import ReqClient  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"blocked_by_obs_websocket_client_missing: {exc}") from exc
    password = os.environ.get(str(profile.get("obs_password_env") or "OBS_WEBSOCKET_PASSWORD")) or None
    client = ReqClient(
        host=str(profile.get("obs_host") or "127.0.0.1"),
        port=int(profile.get("obs_port") or 4455),
        password=password,
        timeout=5,
    )
    scenes = client.get_scene_list()
    inputs = client.get_input_list()
    scene_names = [getattr(scene, "scene_name", None) or scene.get("sceneName") for scene in getattr(scenes, "scenes", [])]
    input_names = [getattr(item, "input_name", None) or item.get("inputName") for item in getattr(inputs, "inputs", [])]
    expected_scene = str(profile.get("obs_scene") or "")
    expected_source = str(profile.get("obs_source") or "")
    if expected_scene and expected_scene not in scene_names:
        raise RuntimeError("blocked_by_obs_scene_missing")
    if expected_source and expected_source not in input_names:
        raise RuntimeError("blocked_by_obs_source_missing")
    return {
        "status": "connected",
        "websocket_connected": True,
        "scene_detected": bool(expected_scene),
        "source_detected": bool(expected_source),
        "active_scene": getattr(client.get_current_program_scene(), "current_program_scene_name", None),
        "scene_count": len(scene_names),
        "source_count": len(input_names),
        "scene_names": scene_names,
        "source_names": input_names,
        "test_source": False,
        "production_capture": True,
    }


def capture_frames(args: argparse.Namespace, profile: dict[str, Any], run_dir: Path, target_total: int) -> list[Path]:
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "plan":
        raise RuntimeError("blocked_by_no_user_prepared_game_profiles")
    if args.mode == "dry-run":
        return capture_ffmpeg_testsrc(raw_dir, target_total, args.ffmpeg_path)
    return capture_obs_source_screenshots(profile, raw_dir, target_total)


def capture_ffmpeg_testsrc(raw_dir: Path, target_total: int, ffmpeg_path: str) -> list[Path]:
    ffmpeg = Path(ffmpeg_path) if ffmpeg_path else find_executable("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("blocked_by_ffmpeg_missing")
    output_pattern = raw_dir / "ffmpeg_testsrc_%04d.png"
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=duration={max(target_total, 1)}:size=1280x720:rate=1",
        "-frames:v",
        str(target_total),
        str(output_pattern),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg_testsrc failed")
    return sorted(raw_dir.glob("ffmpeg_testsrc_*.png"))


def capture_obs_source_screenshots(profile: dict[str, Any], raw_dir: Path, target_total: int) -> list[Path]:
    try:
        from obsws_python import ReqClient  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"blocked_by_obs_websocket_client_missing: {exc}") from exc
    password = os.environ.get(str(profile.get("obs_password_env") or "OBS_WEBSOCKET_PASSWORD")) or None
    client = ReqClient(
        host=str(profile.get("obs_host") or "127.0.0.1"),
        port=int(profile.get("obs_port") or 4455),
        password=password,
        timeout=5,
    )
    source = str(profile.get("obs_source") or "")
    if not source:
        raise RuntimeError("blocked_by_obs_source_not_configured")
    interval = max(0.05, int(profile.get("frame_interval_ms", 500)) / 1000)
    paths: list[Path] = []
    for index in range(1, target_total + 1):
        response = client.get_source_screenshot(source, "png", 0, 0, 100)
        encoded = getattr(response, "image_data", None) or getattr(response, "imageData", None)
        if not encoded:
            raise RuntimeError("blocked_by_obs_no_frame")
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]
        output = raw_dir / f"obs_frame_{index:04d}.png"
        output.write_bytes(base64.b64decode(encoded))
        paths.append(output)
        time.sleep(interval)
    return paths


def evaluate_frames(
    frame_paths: list[Path],
    run_dir: Path,
    run_id: str,
    profile: dict[str, Any],
    quality_policy: dict[str, Any],
    mode: str,
    obs_result: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    gate = OneGameQualityGate(quality_policy)
    records: list[dict[str, Any]] = []
    counts = {
        "attempted": 0,
        "valid_total": 0,
        "high_count": 0,
        "fixed_count": 0,
        "low_count": 0,
        "duplicate_count": 0,
        "black_screen_count": 0,
        "white_screen_count": 0,
        "low_quality_count": 0,
        "stuck_frame_count": 0,
        "rejected_count": 0,
    }
    for index, source_path in enumerate(frame_paths, start=1):
        counts["attempted"] += 1
        image_id = f"{run_id}:{index:04d}"
        quality = gate.evaluate(image_id, source_path)
        bucket = "high" if quality.quality_status == "accepted" else "rejected"
        if quality.quality_status == "accepted":
            counts["valid_total"] += 1
            counts["high_count"] += 1
        else:
            if quality.reject_reason in {"duplicate", "stuck_frame"}:
                counts["duplicate_count"] += 1
                if quality.reject_reason == "stuck_frame":
                    counts["stuck_frame_count"] += 1
            else:
                counts["rejected_count"] += 1
                if quality.reject_reason == "black_screen":
                    counts["black_screen_count"] += 1
                if quality.reject_reason == "white_screen":
                    counts["white_screen_count"] += 1
                if quality.reject_reason == "low_quality":
                    counts["low_quality_count"] += 1
        destination = run_dir / bucket / source_path.name
        shutil.copy2(source_path, destination)
        records.append(
            {
                "run_id": run_id,
                "frame_index": index,
                "timestamp": now_iso(),
                "capture_method": "ffmpeg_testsrc" if mode == "dry-run" else "obs_video_frame_capture",
                "source_method": "ffmpeg_testsrc" if mode == "dry-run" else "obs_websocket_source_screenshot",
                "obs_scene": profile.get("obs_scene") or obs_result.get("active_scene"),
                "obs_source": profile.get("obs_source") or "ffmpeg_testsrc",
                "source_resolution": [quality.width, quality.height],
                "output_resolution": [quality.width, quality.height],
                "source_width": quality.width,
                "source_height": quality.height,
                "output_width": quality.width,
                "output_height": quality.height,
                "bucket": bucket,
                "file_path": str(destination),
                "quality_status": quality.quality_status,
                "dedup_status": quality.dedup_status,
                "is_duplicate": quality.dedup_status == "duplicate",
                "duplicate_of": quality.duplicate_of,
                "content_hash": quality.content_hash,
                "phash": quality.phash,
                "dhash": quality.dhash,
                "brightness_mean": quality.brightness_mean,
                "brightness_std": quality.brightness_std,
                "laplacian_var": quality.laplacian_var,
                "black_ratio": quality.black_ratio,
                "white_ratio": quality.white_ratio,
                "edge_density": quality.edge_density,
                "entropy": quality.entropy,
                "frame_diff": quality.frame_diff,
                "reject_reason": quality.reject_reason,
                "rejected_reason": quality.reject_reason,
                "test_source": mode == "dry-run",
                "production_capture": mode == "real",
                "source_type": "test_source" if mode == "dry-run" else "game_window",
                "online_inference": False,
                "model_action_control": False,
            }
        )
    return records, counts


def write_outputs(
    run_dir: Path,
    run_id: str,
    profile: dict[str, Any],
    mode: str,
    started_at: str,
    records: list[dict[str, Any]],
    summary_counts: dict[str, int],
    target_total: int,
    action_log: Path,
    obs_result: dict[str, Any],
) -> None:
    meta_path = run_dir / "meta.jsonl"
    write_jsonl(meta_path, records)
    reject_distribution: dict[str, int] = {}
    for record in records:
        reason = record.get("reject_reason")
        if reason:
            reject_distribution[str(reason)] = reject_distribution.get(str(reason), 0) + 1
    quality_report = {
        "schema_version": "p14.5-onegame-quality-report",
        "run_id": run_id,
        **summary_counts,
        "reject_reason_distribution": reject_distribution,
        "online_inference": False,
        "model_action_control": False,
        "ocr_analysis_count": 0,
        "showui_analysis_count": 0,
    }
    (run_dir / "quality_report.json").write_text(json.dumps(quality_report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "schema_version": "p14.5-onegame-mvp",
        "run_id": run_id,
        "task_id": run_id,
        "worker_id": "worker_pc_game_w1",
        "game_id": profile.get("game_id"),
        "game_name": profile.get("game_name"),
        "status": "capture_completed" if summary_counts["valid_total"] >= min(60, max(1, int(target_total * 0.6))) else "failed_low_yield",
        "target_total": target_total,
        "started_at": started_at,
        "finished_at": now_iso(),
        "capture_method": "ffmpeg_testsrc" if mode == "dry-run" else "obs_video_frame_capture",
        "source_method": "ffmpeg_testsrc" if mode == "dry-run" else "obs_websocket_source_screenshot",
        "test_source": mode == "dry-run",
        "production_capture": mode == "real",
        "online_inference": False,
        "model_action_control": False,
        "automatic_upload": False,
        "automatic_cleanup": False,
        "behavior_pack": profile.get("behavior_pack"),
        "behavior_actions_path": str(action_log),
        "meta_path": str(meta_path),
        "quality_report_path": str(run_dir / "quality_report.json"),
        "artifacts_root": str(run_dir),
        "upload_status": "pending",
        "obs": obs_result,
        **summary_counts,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(
        run_dir / "run.log",
        [
            {"event": "onegame_mvp_started", "run_id": run_id, "timestamp": started_at},
            {"event": "onegame_mvp_finished", "run_id": run_id, "timestamp": now_iso(), "status": summary["status"]},
        ],
    )


def write_blocked_outputs(run_dir: Path, run_id: str, profile: dict[str, Any], mode: str, started_at: str, reason: str) -> dict[str, Any]:
    create_run_dirs(run_dir)
    summary = {
        "schema_version": "p14.5-onegame-mvp",
        "run_id": run_id,
        "worker_id": "worker_pc_game_w1",
        "game_id": profile.get("game_id"),
        "status": "blocked",
        "failure_reason": reason,
        "target_total": profile.get("target_total", 100),
        "attempted": 0,
        "valid_total": 0,
        "duplicate_count": 0,
        "rejected_count": 0,
        "capture_method": "ffmpeg_testsrc" if mode == "dry-run" else "obs_video_frame_capture",
        "test_source": mode == "dry-run",
        "production_capture": False,
        "online_inference": False,
        "model_action_control": False,
        "automatic_upload": False,
        "automatic_cleanup": False,
        "started_at": started_at,
        "finished_at": now_iso(),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "meta.jsonl").write_text("", encoding="utf-8")
    (run_dir / "quality_report.json").write_text(json.dumps({"run_id": run_id, "status": "blocked", "reason": reason}, indent=2), encoding="utf-8")
    write_jsonl(run_dir / "run.log", [{"event": "blocked", "run_id": run_id, "reason": reason, "timestamp": now_iso()}])
    return summary


def write_behavior_actions(run_dir: Path, behavior_pack: dict[str, Any], execute_real: bool) -> Path:
    action_log = run_dir / "action_log.jsonl"
    actions = behavior_pack.get("actions") or []
    blocked = set(behavior_pack.get("blocked_actions") or []) | set(behavior_pack.get("blocked_contexts") or [])
    if execute_real:
        raise RuntimeError("real behavior execution is disabled for OneGame MVP until explicit operator approval")
    rows = []
    for index, action in enumerate(actions, start=1):
        action_type = str(action.get("type") or "")
        action_name = str(action.get("name") or f"action_{index}")
        risk_flags = set(action.get("risk_flags") or [])
        unsafe = action_type in SAFE_BLOCKED_ACTIONS or action_name in SAFE_BLOCKED_ACTIONS or bool(risk_flags & SAFE_BLOCKED_ACTIONS) or bool(blocked & SAFE_BLOCKED_ACTIONS and action_type in SAFE_BLOCKED_ACTIONS)
        rows.append(
            {
                "index": index,
                "action_name": action_name,
                "action_type": action_type,
                "duration_ms": action.get("duration_ms"),
                "dry_run": True,
                "executed": False,
                "skipped": unsafe,
                "risk_flags": sorted(risk_flags | ({action_type} if unsafe else set())),
                "timestamp": now_iso(),
            }
        )
    write_jsonl(action_log, rows)
    return action_log


def inject_quality_fixtures(raw_dir: Path, frame_paths: list[Path]) -> list[Path]:
    fixtures: list[Path] = []
    black = raw_dir / "fixture_black_screen.png"
    write_solid_png(black, 1280, 720, 0)
    fixtures.append(black)
    if frame_paths:
        duplicate = raw_dir / "fixture_duplicate.png"
        shutil.copy2(frame_paths[0], duplicate)
        fixtures.append(duplicate)
    return fixtures


def read_png_pixels(path: Path) -> PngPixels:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a png: {path}")
    offset = 8
    width = height = color_type = bit_depth = None
    chunks: list[bytes] = []
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk_data[:10])[:4]
        elif chunk_type == b"IDAT":
            chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break
    if width is None or height is None or bit_depth != 8 or color_type not in {0, 2, 6}:
        raise ValueError(f"unsupported png format: {path}")
    channels = {0: 1, 2: 3, 6: 4}[int(color_type)]
    stride = int(width) * channels
    raw = zlib.decompress(b"".join(chunks))
    rows: list[bytearray] = []
    cursor = 0
    previous = bytearray(stride)
    for _ in range(int(height)):
        filter_type = raw[cursor]
        cursor += 1
        row = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        unfilter(row, previous, filter_type, channels)
        rows.append(row)
        previous = row
    gray: list[int] = []
    for row in rows:
        for x in range(0, stride, channels):
            if channels == 1:
                gray.append(row[x])
            else:
                gray.append(int(row[x] * 0.299 + row[x + 1] * 0.587 + row[x + 2] * 0.114))
    return PngPixels(width=int(width), height=int(height), gray=gray)


def unfilter(row: bytearray, previous: bytearray, filter_type: int, bpp: int) -> None:
    for i in range(len(row)):
        left = row[i - bpp] if i >= bpp else 0
        up = previous[i]
        up_left = previous[i - bpp] if i >= bpp else 0
        if filter_type == 1:
            row[i] = (row[i] + left) & 0xFF
        elif filter_type == 2:
            row[i] = (row[i] + up) & 0xFF
        elif filter_type == 3:
            row[i] = (row[i] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            row[i] = (row[i] + paeth(left, up, up_left)) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"unsupported png filter: {filter_type}")


def paeth(left: int, up: int, up_left: int) -> int:
    p = left + up - up_left
    pa = abs(p - left)
    pb = abs(p - up)
    pc = abs(p - up_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return up_left


def write_solid_png(path: Path, width: int, height: int, value: int) -> None:
    raw_rows = []
    pixel = bytes([value, value, value])
    for _ in range(height):
        raw_rows.append(b"\x00" + pixel * width)
    payload = zlib.compress(b"".join(raw_rows))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", payload)
        + png_chunk(b"IEND", b"")
    )


def png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    import binascii

    crc = binascii.crc32(chunk_type + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)


def average_hash(gray: list[int], width: int, height: int, size: int = 8) -> str:
    sample = sample_gray(gray, width, height, size, size)
    avg = sum(sample) / max(len(sample), 1)
    bits = ["1" if value >= avg else "0" for value in sample]
    return bits_to_hex(bits)


def difference_hash(gray: list[int], width: int, height: int, size: int = 8) -> str:
    sample = sample_gray(gray, width, height, size + 1, size)
    bits = []
    for y in range(size):
        row = sample[y * (size + 1) : (y + 1) * (size + 1)]
        for x in range(size):
            bits.append("1" if row[x] > row[x + 1] else "0")
    return bits_to_hex(bits)


def sample_gray(gray: list[int], width: int, height: int, out_w: int, out_h: int) -> list[int]:
    values = []
    for y in range(out_h):
        src_y = min(height - 1, int((y + 0.5) * height / out_h))
        for x in range(out_w):
            src_x = min(width - 1, int((x + 0.5) * width / out_w))
            values.append(gray[src_y * width + src_x])
    return values


def bits_to_hex(bits: list[str]) -> str:
    value = int("".join(bits), 2) if bits else 0
    return f"{value:0{max(1, math.ceil(len(bits) / 4))}x}"


def hamming_hex(left: str, right: str) -> int:
    return bin(int(left, 16) ^ int(right, 16)).count("1")


def mean_abs_diff(left: list[int], right: list[int]) -> float:
    if len(left) != len(right):
        return 999.0
    return sum(abs(a - b) for a, b in zip(left, right)) / max(len(left), 1)


def mean_adjacent_diff(gray: list[int], width: int, height: int) -> float:
    diffs = []
    step = max(1, width * height // 20000)
    for y in range(0, height, step):
        base = y * width
        for x in range(1, width, step):
            diffs.append(abs(gray[base + x] - gray[base + x - 1]))
    return sum(diffs) / max(len(diffs), 1)


def laplacian_variance(gray: list[int], width: int, height: int) -> float:
    values = []
    x_step = max(1, width // 160)
    y_step = max(1, height // 90)
    for y in range(1, height - 1, y_step):
        for x in range(1, width - 1, x_step):
            center = gray[y * width + x]
            lap = gray[(y - 1) * width + x] + gray[(y + 1) * width + x] + gray[y * width + x - 1] + gray[y * width + x + 1] - 4 * center
            values.append(lap)
    mean = sum(values) / max(len(values), 1)
    return sum((value - mean) ** 2 for value in values) / max(len(values), 1)


def grayscale_entropy(gray: list[int]) -> float:
    hist = [0] * 256
    for value in gray:
        hist[value] += 1
    total = len(gray)
    entropy = 0.0
    for count in hist:
        if count:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def stddev(values: list[int], mean: float) -> float:
    return math.sqrt(sum((value - mean) ** 2 for value in values) / max(len(values), 1))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_run_dirs(run_dir: Path) -> None:
    for folder in [run_dir, run_dir / "raw", run_dir / "fixed", run_dir / "low", run_dir / "high", run_dir / "rejected"]:
        folder.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_executable(name: str) -> Path | None:
    found = shutil.which(name)
    return Path(found) if found else None


def default_run_id(mode: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "dryrun" if mode == "dry-run" else "real"
    return f"p14_5_onegame_mvp_{suffix}_{stamp}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
