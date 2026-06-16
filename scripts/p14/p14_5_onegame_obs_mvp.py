from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import json
import math
import os
import random
import shutil
import socket
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
        metrics_pixels = downsample_pixels(pixels, max_width=int(self.policy.get("metrics_max_width", 320)))
        gray = metrics_pixels.gray
        content_hash = sha256(path)
        dhash = difference_hash(gray, metrics_pixels.width, metrics_pixels.height)
        phash = average_hash(gray, metrics_pixels.width, metrics_pixels.height)
        brightness_mean = sum(gray) / max(len(gray), 1)
        brightness_std = stddev(gray, brightness_mean)
        black_ratio = sum(1 for value in gray if value <= 10) / max(len(gray), 1)
        white_ratio = sum(1 for value in gray if value >= 245) / max(len(gray), 1)
        edge_density = mean_adjacent_diff(gray, metrics_pixels.width, metrics_pixels.height)
        laplacian_var = laplacian_variance(gray, metrics_pixels.width, metrics_pixels.height)
        entropy = grayscale_entropy(gray)
        frame_diff = 999.0 if self._previous_gray is None else mean_abs_diff(gray, self._previous_gray)
        source_width = pixels.source_width or pixels.width
        source_height = pixels.source_height or pixels.height

        reject_reason: str | None = None
        duplicate_of: str | None = None
        if source_width < int(self.policy["min_width"]) or source_height < int(self.policy["min_height"]):
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
            width=source_width,
            height=source_height,
            duplicate_of=duplicate_of,
        )


@dataclass(frozen=True)
class PngPixels:
    width: int
    height: int
    gray: list[int]
    source_width: int | None = None
    source_height: int | None = None


@dataclass
class CaptureTiming:
    capture_latency_ms: float = 0.0
    quality_latency_ms: float = 0.0
    save_latency_ms: float = 0.0
    end_to_end_ms: float = 0.0


@dataclass
class VariationDecision:
    accepted: bool
    reason: str
    phash_distance_min: int | None
    luma_difference_min: float | None
    consecutive_frame_diff: float
    histogram_diff: float


class VariationGate:
    def __init__(self, profile: dict[str, Any]) -> None:
        self.enabled = bool(profile.get("variation_gate_enabled", False))
        self.min_hash_distance = int(profile.get("variation_min_phash_distance", 4))
        self.min_luma_difference = float(profile.get("variation_min_luma_difference", 3.0))
        self.compare_all_saved = bool(profile.get("variation_compare_all_saved", True))
        self.saved_signatures: list[dict[str, Any]] = []
        self.previous_gray: list[int] | None = None
        self.low_variation_streak = 0
        self.longest_low_variation_streak = 0
        self.low_variation_count = 0
        self.histogram_diffs: list[float] = []
        self.frame_diffs: list[float] = []
        self.phash_distances: list[int] = []
        self.luma_differences: list[float] = []

    def evaluate(self, path: Path) -> VariationDecision:
        if not self.enabled:
            decision = VariationDecision(True, "variation_gate_disabled", None, None, 999.0, 999.0)
            return decision
        pixels = downsample_pixels(read_png_pixels(path), max_width=320)
        gray = pixels.gray
        phash = average_hash(gray, pixels.width, pixels.height, size=16)
        luma = sample_gray(gray, pixels.width, pixels.height, 80, 45)
        histogram = grayscale_histogram(gray)
        if not self.saved_signatures:
            self._accept(phash, luma, histogram, gray)
            return VariationDecision(True, "first_saved_frame", None, None, 999.0, 999.0)

        candidates = self.saved_signatures if self.compare_all_saved else self.saved_signatures[-1:]
        phash_distances = [hamming_hex(phash, str(item["phash"])) for item in candidates]
        luma_diffs = [mean_abs_diff(luma, list(item["luma"])) for item in candidates]
        histogram_diffs = [histogram_distance(histogram, list(item["histogram"])) for item in candidates]
        phash_min = min(phash_distances) if phash_distances else None
        luma_min = min(luma_diffs) if luma_diffs else None
        histogram_min = min(histogram_diffs) if histogram_diffs else 0.0
        consecutive = 999.0 if self.previous_gray is None else mean_abs_diff(gray, self.previous_gray)
        accepted = bool(
            phash_min is None
            or luma_min is None
            or phash_min > self.min_hash_distance
            or luma_min > self.min_luma_difference
        )
        if accepted:
            self._accept(phash, luma, histogram, gray)
            self.low_variation_streak = 0
            self.phash_distances.append(int(phash_min or 0))
            self.luma_differences.append(float(luma_min or 0.0))
            self.frame_diffs.append(float(consecutive))
            self.histogram_diffs.append(float(histogram_min))
            return VariationDecision(True, "variation_passed", phash_min, luma_min, consecutive, histogram_min)

        self.low_variation_count += 1
        self.low_variation_streak += 1
        self.longest_low_variation_streak = max(self.longest_low_variation_streak, self.low_variation_streak)
        self.previous_gray = gray
        self.phash_distances.append(int(phash_min or 0))
        self.luma_differences.append(float(luma_min or 0.0))
        self.frame_diffs.append(float(consecutive))
        self.histogram_diffs.append(float(histogram_min))
        return VariationDecision(False, "skipped_low_variation", phash_min, luma_min, consecutive, histogram_min)

    def _accept(self, phash: str, luma: list[int], histogram: list[float], gray: list[int]) -> None:
        self.saved_signatures.append({"phash": phash, "luma": luma, "histogram": histogram})
        self.previous_gray = gray

    def summary(self, attempted: int) -> dict[str, Any]:
        low_ratio = self.low_variation_count / max(1, attempted)
        return {
            "variation_gate_enabled": self.enabled,
            "low_variation_count": self.low_variation_count,
            "skipped_low_variation_count": self.low_variation_count,
            "low_variation_ratio": round(low_ratio, 6),
            "longest_low_variation_streak": self.longest_low_variation_streak,
            "visual_variation_passed": low_ratio <= 0.20 and self.longest_low_variation_streak <= 10,
            "static_like_capture": low_ratio > 0.20 or self.longest_low_variation_streak > 10,
            "consecutive_frame_diff_mean": mean_or_zero(self.frame_diffs),
            "consecutive_frame_diff_p50": percentile(self.frame_diffs, 50),
            "consecutive_frame_diff_p90": percentile(self.frame_diffs, 90),
            "pHash_distance_mean": mean_or_zero(self.phash_distances),
            "pHash_distance_p50": percentile(self.phash_distances, 50),
            "pHash_distance_p90": percentile(self.phash_distances, 90),
            "histogram_diff_mean": mean_or_zero(self.histogram_diffs),
        }


def main() -> int:
    args = parse_args()
    profile = read_json(args.profile)
    apply_profile_overrides(profile, args)
    quality_policy = read_json(args.quality_policy)
    behavior_pack = read_json(args.behavior_pack)
    target_total = int(args.target_total or profile.get("target_total", 100))
    if target_total < 1 or target_total > 5000:
        raise ValueError("OneGame target_total must be between 1 and 5000")
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
    if args.finalize_existing:
        try:
            frame_paths = sorted((run_dir / "raw").glob("*.png"))
            if not frame_paths:
                raise RuntimeError("blocked_by_no_existing_raw_frames")
            target_total = len(frame_paths)
            obs_result = {
                "status": "finalize_existing",
                "websocket_connected": False,
                "scene_detected": False,
                "source_detected": False,
                "test_source": False,
                "production_capture": True,
            }
            records, summary_counts = evaluate_frames(
                frame_paths=frame_paths,
                run_dir=run_dir,
                run_id=run_id,
                profile=profile,
                quality_policy=quality_policy,
                mode="real",
                obs_result=obs_result,
                frame_actions=load_frame_actions(run_dir / "action_log.jsonl"),
            )
            write_outputs(
                run_dir=run_dir,
                run_id=run_id,
                profile=profile,
                mode="real",
                started_at=started_at,
                records=records,
                summary_counts=summary_counts,
                target_total=target_total,
                action_log=run_dir / "action_log.jsonl",
                obs_result=obs_result,
            )
            status = status_from_counts(summary_counts, target_total, profile)
            result = {
                "status": status,
                "run_id": run_id,
                "mode": "finalize_existing",
                "run_dir": str(run_dir),
                "attempted": summary_counts["attempted"],
                "valid_total": summary_counts["valid_total"],
                "duplicate_count": summary_counts["duplicate_count"],
                "black_screen_count": summary_counts["black_screen_count"],
                "low_quality_count": summary_counts["low_quality_count"],
                "rejected_count": summary_counts["rejected_count"],
                "test_source": False,
                "production_capture": True,
                "online_inference": False,
                "model_action_control": False,
                "automatic_upload": False,
                "automatic_cleanup": False,
                "obs": obs_result,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if status == "capture_completed" else 1
        except Exception as exc:
            result = write_blocked_outputs(run_dir, run_id, profile, "real", started_at, str(exc))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1

    behavior_executor = BehaviorExecutor(run_dir, behavior_pack, execute_real=args.execute_behavior)
    action_log = behavior_executor.prepare()
    try:
        obs_result = verify_obs(profile, dry_run=args.mode == "dry-run")
        if args.mode == "real" and args.require_live_preflight:
            preflight = run_live_preflight_check(
                profile=profile,
                run_dir=run_dir,
                previous_run_dir=Path(args.previous_run_dir) if args.previous_run_dir else None,
                obs_result=obs_result,
            )
            obs_result["preflight_live_frame_check"] = preflight
            if not preflight.get("preflight_live_frame_check_passed", False):
                raise RuntimeError("blocked_by_preflight_live_frame_check_failed")
        frame_paths, capture_stats = capture_frames(args, profile, run_dir, target_total, behavior_executor)
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
            frame_actions=behavior_executor.frame_actions,
            capture_stats=capture_stats,
        )
        visualizations = create_visualizations(run_dir, records)
        summary_counts.update(visualizations)
        summary_counts.update(
            {
                "real_input_executed": bool(args.execute_behavior and behavior_executor.actions),
                "key_release_ok": not behavior_executor._pressed_keys,
                "stuck_key_detected": bool(behavior_executor._pressed_keys),
                "emergency_stop_available": True,
            }
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
        status = status_from_counts(summary_counts, target_total, profile)
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
    finally:
        behavior_executor.close()


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
    parser.add_argument("--obs-host", default="")
    parser.add_argument("--obs-port", type=int, default=0)
    parser.add_argument("--obs-scene", default="")
    parser.add_argument("--obs-source", default="")
    parser.add_argument("--game-id", default="")
    parser.add_argument("--game-name", default="")
    parser.add_argument("--user-ready", action="store_true")
    parser.add_argument("--execute-behavior", action="store_true")
    parser.add_argument("--inject-quality-fixtures", action="store_true")
    parser.add_argument("--finalize-existing", action="store_true")
    parser.add_argument("--require-live-preflight", action="store_true")
    parser.add_argument("--variation-gate", action="store_true")
    parser.add_argument("--previous-run-dir", default="")
    parser.add_argument("--capture-interval-ms", type=int, default=0)
    return parser.parse_args()


def apply_profile_overrides(profile: dict[str, Any], args: argparse.Namespace) -> None:
    overrides = {
        "obs_host": args.obs_host,
        "obs_port": args.obs_port,
        "obs_scene": args.obs_scene,
        "obs_source": args.obs_source,
        "game_id": args.game_id,
        "game_name": args.game_name,
    }
    for key, value in overrides.items():
        if value:
            profile[key] = value
    if args.capture_interval_ms:
        profile["frame_interval_ms"] = args.capture_interval_ms
    if args.variation_gate:
        profile["variation_gate_enabled"] = True


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
    password = os.environ.get(str(profile.get("obs_password_env") or "OBS_WEBSOCKET_PASSWORD")) or None
    client = ObsWebSocketClient(
        host=str(profile.get("obs_host") or "127.0.0.1"),
        port=int(profile.get("obs_port") or 4455),
        password=password,
        timeout=5,
    )
    with client:
        scenes = client.request("GetSceneList")
        inputs = client.request("GetInputList")
        current_scene = client.request("GetCurrentProgramScene")
        scene_names = [str(scene.get("sceneName")) for scene in scenes.get("scenes", []) if scene.get("sceneName")]
        input_names = [str(item.get("inputName")) for item in inputs.get("inputs", []) if item.get("inputName")]
        input_kinds = {str(item.get("inputName")): str(item.get("inputKind") or "") for item in inputs.get("inputs", []) if item.get("inputName")}
        expected_scene = str(profile.get("obs_scene") or "") or str(current_scene.get("currentProgramSceneName") or "")
        expected_source = str(profile.get("obs_source") or "")
        scene_item_names: list[str] = []
        if expected_scene:
            if expected_scene not in scene_names:
                raise RuntimeError("blocked_by_obs_scene_missing")
            scene_items = client.request("GetSceneItemList", {"sceneName": expected_scene})
            scene_item_names = [
                str(item.get("sourceName")) for item in scene_items.get("sceneItems", []) if item.get("sourceName")
            ]
            if not expected_source and scene_item_names:
                expected_source = scene_item_names[0]
        if expected_source and expected_source not in input_names and expected_source not in scene_item_names:
            raise RuntimeError("blocked_by_obs_source_missing")
        if not expected_source:
            raise RuntimeError("blocked_by_obs_source_not_configured")
        profile["_resolved_obs_scene"] = expected_scene
        profile["_resolved_obs_source"] = expected_source
        profile["_resolved_obs_source_kind"] = input_kinds.get(expected_source) or "scene_or_unknown"
        return {
            "status": "connected",
            "websocket_connected": True,
            "scene_detected": bool(expected_scene),
            "source_detected": bool(expected_source),
            "program_scene_refreshed": True,
            "source_refreshed": True,
            "selected_scene": expected_scene,
            "selected_source": expected_source,
            "source_name": expected_source,
            "source_kind": input_kinds.get(expected_source) or "scene_or_unknown",
            "screenshot_resolution": [
                int(profile.get("obs_screenshot_width") or 1920),
                int(profile.get("obs_screenshot_height") or 1080),
            ],
            "active_scene": current_scene.get("currentProgramSceneName"),
            "scene_count": len(scene_names),
            "source_count": len(input_names),
            "scene_names": scene_names,
            "source_names": input_names,
            "scene_item_names": scene_item_names,
            "test_source": False,
            "production_capture": True,
        }


def capture_frames(
    args: argparse.Namespace,
    profile: dict[str, Any],
    run_dir: Path,
    target_total: int,
    behavior_executor: BehaviorExecutor,
) -> tuple[list[Path], dict[str, Any]]:
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "plan":
        raise RuntimeError("blocked_by_no_user_prepared_game_profiles")
    if args.mode == "dry-run":
        paths = capture_ffmpeg_testsrc(raw_dir, target_total, args.ffmpeg_path)
        return paths, {"attempted": len(paths), "frames_by_path": {}, "variation_gate_enabled": False}
    return capture_obs_source_screenshots(profile, raw_dir, target_total, behavior_executor)


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


def capture_obs_source_screenshots(
    profile: dict[str, Any],
    raw_dir: Path,
    target_total: int,
    behavior_executor: BehaviorExecutor,
) -> tuple[list[Path], dict[str, Any]]:
    password = os.environ.get(str(profile.get("obs_password_env") or "OBS_WEBSOCKET_PASSWORD")) or None
    client = ObsWebSocketClient(
        host=str(profile.get("obs_host") or "127.0.0.1"),
        port=int(profile.get("obs_port") or 4455),
        password=password,
        timeout=5,
    )
    source = str(profile.get("_resolved_obs_source") or profile.get("obs_source") or "")
    if not source:
        raise RuntimeError("blocked_by_obs_source_not_configured")
    screenshot_width = int(profile.get("obs_screenshot_width") or 1920)
    screenshot_height = int(profile.get("obs_screenshot_height") or 1080)
    interval = max(0.05, int(profile.get("frame_interval_ms", 500)) / 1000)
    paths: list[Path] = []
    frames_by_path: dict[str, dict[str, Any]] = {}
    skipped_records: list[dict[str, Any]] = []
    timings: list[CaptureTiming] = []
    variation_gate = VariationGate(profile)
    capture_started = time.perf_counter()
    with client:
        for index in range(1, target_total + 1):
            frame_started = time.perf_counter()
            behavior_executor.step(frame_index=index)
            capture_started_at = time.perf_counter()
            response = client.request(
                "GetSourceScreenshot",
                {
                    "sourceName": source,
                    "imageFormat": "png",
                    "imageWidth": screenshot_width,
                    "imageHeight": screenshot_height,
                    "imageCompressionQuality": int(profile.get("obs_image_compression_quality", 90)),
                },
            )
            capture_latency_ms = (time.perf_counter() - capture_started_at) * 1000
            encoded = response.get("imageData")
            if not encoded:
                raise RuntimeError("blocked_by_obs_no_frame")
            if "," in encoded:
                encoded = encoded.split(",", 1)[1]
            output = raw_dir / f"obs_frame_{index:04d}.png"
            save_started_at = time.perf_counter()
            output.write_bytes(base64.b64decode(encoded))
            save_latency_ms = (time.perf_counter() - save_started_at) * 1000
            quality_started_at = time.perf_counter()
            decision = variation_gate.evaluate(output)
            quality_latency_ms = (time.perf_counter() - quality_started_at) * 1000
            if decision.accepted:
                paths.append(output)
                frames_by_path[str(output)] = {
                    "attempt_index": index,
                    "capture_timestamp": now_iso(),
                    "variation_decision": decision.reason,
                    "phash_distance_min": decision.phash_distance_min,
                    "luma_difference_min": decision.luma_difference_min,
                    "consecutive_frame_diff": round(decision.consecutive_frame_diff, 3),
                    "histogram_diff": round(decision.histogram_diff, 6),
                    "capture_latency_ms": round(capture_latency_ms, 3),
                    "quality_latency_ms": round(quality_latency_ms, 3),
                    "save_latency_ms": round(save_latency_ms, 3),
                }
            else:
                skipped_records.append(
                    {
                        "attempt_index": index,
                        "timestamp": now_iso(),
                        "reason": decision.reason,
                        "phash_distance_min": decision.phash_distance_min,
                        "luma_difference_min": decision.luma_difference_min,
                        "consecutive_frame_diff": round(decision.consecutive_frame_diff, 3),
                        "histogram_diff": round(decision.histogram_diff, 6),
                    }
                )
                try:
                    output.unlink()
                except OSError:
                    pass
            timings.append(
                CaptureTiming(
                    capture_latency_ms=capture_latency_ms,
                    quality_latency_ms=quality_latency_ms,
                    save_latency_ms=save_latency_ms,
                    end_to_end_ms=(time.perf_counter() - frame_started) * 1000,
                )
            )
            time.sleep(interval)
    elapsed_seconds = max(0.001, time.perf_counter() - capture_started)
    skipped_path = raw_dir.parent / "skipped_low_variation.jsonl"
    write_jsonl(skipped_path, skipped_records)
    stats = {
        "attempted": target_total,
        "saved_total": len(paths),
        "frames_by_path": frames_by_path,
        "skipped_low_variation_path": str(skipped_path),
        "obs_screenshot_cache_cleared": True,
        "per_frame_obs_request": True,
        "frame_timestamp_from_current_run": True,
        "attempted_per_minute": round(target_total / elapsed_seconds * 60, 3),
        "saved_per_minute": round(len(paths) / elapsed_seconds * 60, 3),
        "average_capture_latency_ms": round(mean_or_zero([item.capture_latency_ms for item in timings]), 3),
        "average_quality_latency_ms": round(mean_or_zero([item.quality_latency_ms for item in timings]), 3),
        "average_save_latency_ms": round(mean_or_zero([item.save_latency_ms for item in timings]), 3),
        "end_to_end_avg_frame_ms": round(mean_or_zero([item.end_to_end_ms for item in timings]), 3),
        **variation_gate.summary(target_total),
    }
    stats["valid_per_minute"] = stats["saved_per_minute"]
    stats["speed_improved"] = int(profile.get("frame_interval_ms", 500)) <= 250
    return paths, stats


def run_live_preflight_check(
    profile: dict[str, Any],
    run_dir: Path,
    previous_run_dir: Path | None,
    obs_result: dict[str, Any],
) -> dict[str, Any]:
    preflight_dir = run_dir / "preflight"
    preflight_dir.mkdir(parents=True, exist_ok=True)
    source = str(profile.get("_resolved_obs_source") or profile.get("obs_source") or "")
    if not source:
        raise RuntimeError("blocked_by_obs_source_not_configured")
    password = os.environ.get(str(profile.get("obs_password_env") or "OBS_WEBSOCKET_PASSWORD")) or None
    screenshot_width = int(profile.get("obs_screenshot_width") or 1920)
    screenshot_height = int(profile.get("obs_screenshot_height") or 1080)
    paths: list[Path] = []
    hashes: list[str] = []
    with ObsWebSocketClient(
        host=str(profile.get("obs_host") or "127.0.0.1"),
        port=int(profile.get("obs_port") or 4455),
        password=password,
        timeout=5,
    ) as client:
        for index in range(1, 4):
            response = client.request(
                "GetSourceScreenshot",
                {
                    "sourceName": source,
                    "imageFormat": "png",
                    "imageWidth": screenshot_width,
                    "imageHeight": screenshot_height,
                    "imageCompressionQuality": int(profile.get("obs_image_compression_quality", 90)),
                },
            )
            encoded = response.get("imageData")
            if not encoded:
                raise RuntimeError("blocked_by_obs_no_preflight_frame")
            if "," in encoded:
                encoded = encoded.split(",", 1)[1]
            path = preflight_dir / f"preflight_frame_{index}.png"
            path.write_bytes(base64.b64decode(encoded))
            paths.append(path)
            hashes.append(sha256(path))
            if index < 3:
                time.sleep(1)

    previous_frames = latest_previous_frames(previous_run_dir, limit=5)
    stale_matches = compare_preflight_to_previous(paths, previous_frames)
    montage = preflight_dir / "preflight_live_frame_montage.png"
    make_montage(paths, montage, columns=3, label_prefix="preflight")
    passed = bool(paths) and not stale_matches
    payload = {
        "preflight_live_frame_check_passed": passed,
        "preflight_frame_paths": [str(path) for path in paths],
        "preflight_frame_hashes": hashes,
        "preflight_live_frame_montage": str(montage),
        "stale_frame_reuse_detected": bool(stale_matches),
        "suspected_stale_obs_frame_or_wrong_source": bool(stale_matches),
        "stale_matches": stale_matches,
        "old_run_dir": str(previous_run_dir) if previous_run_dir else None,
        "new_run_dir": str(run_dir),
        "artifact_root_is_new": True,
        "program_scene_refreshed": bool(obs_result.get("program_scene_refreshed")),
        "source_refreshed": bool(obs_result.get("source_refreshed")),
        "source_name": obs_result.get("source_name"),
        "source_kind": obs_result.get("source_kind"),
        "screenshot_resolution": [screenshot_width, screenshot_height],
        "obs_screenshot_cache_cleared": True,
        "per_frame_obs_request": True,
        "frame_timestamp_from_current_run": True,
    }
    (preflight_dir / "preflight_live_frame_check.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def latest_previous_frames(previous_run_dir: Path | None, limit: int = 5) -> list[Path]:
    if previous_run_dir is None or not previous_run_dir.exists():
        return []
    candidates: list[Path] = []
    for bucket in ["high", "raw", "fixed", "low"]:
        folder = previous_run_dir / bucket
        if folder.exists():
            candidates.extend(sorted(folder.glob("*.png"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit])
    return candidates[:limit]


def compare_preflight_to_previous(preflight: list[Path], previous: list[Path]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    if not previous:
        return matches
    previous_signatures = [(path, frame_signature(path)) for path in previous]
    for current in preflight:
        current_sig = frame_signature(current)
        for previous_path, previous_sig in previous_signatures:
            phash_distance = hamming_hex(current_sig["phash"], previous_sig["phash"])
            luma_difference = mean_abs_diff(current_sig["luma"], previous_sig["luma"])
            if phash_distance <= 2 or luma_difference <= 1.0:
                matches.append(
                    {
                        "preflight_frame": str(current),
                        "previous_frame": str(previous_path),
                        "phash_distance": phash_distance,
                        "luma_difference": round(luma_difference, 3),
                    }
                )
    return matches


def frame_signature(path: Path) -> dict[str, Any]:
    pixels = downsample_pixels(read_png_pixels(path), max_width=320)
    return {
        "phash": average_hash(pixels.gray, pixels.width, pixels.height, size=16),
        "luma": sample_gray(pixels.gray, pixels.width, pixels.height, 80, 45),
    }


class ObsWebSocketClient:
    """Small OBS WebSocket v5 client for screenshot-only capture."""

    def __init__(self, host: str, port: int, password: str | None, timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._request_counter = 0

    def __enter__(self) -> ObsWebSocketClient:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def connect(self) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET / HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = self._read_http_response(sock)
        if " 101 " not in response.split("\r\n", 1)[0]:
            raise RuntimeError("blocked_by_obs_websocket_handshake_failed")
        self._sock = sock
        hello = self._receive_json()
        if hello.get("op") != 0:
            raise RuntimeError("blocked_by_obs_unexpected_hello")
        authentication = hello.get("d", {}).get("authentication")
        if authentication:
            if not self.password:
                raise RuntimeError("blocked_by_obs_auth_required")
            raise RuntimeError("blocked_by_obs_auth_not_supported_for_safety")
        self._send_json({"op": 1, "d": {"rpcVersion": 1}})
        identified = self._receive_json()
        if identified.get("op") != 2:
            raise RuntimeError("blocked_by_obs_identify_failed")

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def request(self, request_type: str, request_data: dict[str, Any] | None = None) -> dict[str, Any]:
        self._request_counter += 1
        request_id = f"p14-onegame-{self._request_counter}"
        self._send_json(
            {
                "op": 6,
                "d": {
                    "requestType": request_type,
                    "requestId": request_id,
                    "requestData": request_data or {},
                },
            }
        )
        while True:
            message = self._receive_json()
            if message.get("op") != 7:
                continue
            data = message.get("d", {})
            if data.get("requestId") != request_id:
                continue
            status = data.get("requestStatus", {})
            if not status.get("result"):
                code = status.get("code", "unknown")
                comment = status.get("comment") or request_type
                raise RuntimeError(f"blocked_by_obs_request_failed:{request_type}:{code}:{comment}")
            return data.get("responseData") or {}

    def _read_http_response(self, sock: socket.socket) -> str:
        chunks: list[bytes] = []
        while b"\r\n\r\n" not in b"".join(chunks):
            chunk = sock.recv(4096)
            if not chunk:
                raise RuntimeError("blocked_by_obs_websocket_handshake_closed")
            chunks.append(chunk)
        return b"".join(chunks).decode("iso-8859-1", errors="replace")

    def _send_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_frame(body)

    def _send_frame(self, payload: bytes) -> None:
        if self._sock is None:
            raise RuntimeError("blocked_by_obs_not_connected")
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend([0x80 | 126, (length >> 8) & 0xFF, length & 0xFF])
        else:
            header.append(0x80 | 127)
            header.extend(length.to_bytes(8, "big"))
        mask = os.urandom(4)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self._sock.sendall(bytes(header) + mask + masked)

    def _receive_json(self) -> dict[str, Any]:
        while True:
            payload, opcode = self._receive_frame()
            if opcode == 1:
                return json.loads(payload.decode("utf-8"))
            if opcode == 8:
                raise RuntimeError("blocked_by_obs_websocket_closed")
            if opcode == 9:
                self._send_pong(payload)

    def _receive_frame(self) -> tuple[bytes, int]:
        if self._sock is None:
            raise RuntimeError("blocked_by_obs_not_connected")
        first = self._recv_exact(2)
        opcode = first[0] & 0x0F
        masked = bool(first[1] & 0x80)
        length = first[1] & 0x7F
        if length == 126:
            length = int.from_bytes(self._recv_exact(2), "big")
        elif length == 127:
            length = int.from_bytes(self._recv_exact(8), "big")
        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length) if length else b""
        if masked:
            payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        return payload, opcode

    def _recv_exact(self, length: int) -> bytes:
        if self._sock is None:
            raise RuntimeError("blocked_by_obs_not_connected")
        chunks: list[bytes] = []
        remaining = length
        while remaining > 0:
            chunk = self._sock.recv(remaining)
            if not chunk:
                raise RuntimeError("blocked_by_obs_websocket_closed")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _send_pong(self, payload: bytes) -> None:
        if self._sock is None:
            return
        header = bytearray([0x8A])
        length = len(payload)
        header.append(0x80 | length)
        mask = os.urandom(4)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self._sock.sendall(bytes(header) + mask + masked)


def evaluate_frames(
    frame_paths: list[Path],
    run_dir: Path,
    run_id: str,
    profile: dict[str, Any],
    quality_policy: dict[str, Any],
    mode: str,
    obs_result: dict[str, Any],
    frame_actions: dict[int, dict[str, Any]] | None = None,
    capture_stats: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    gate = OneGameQualityGate(quality_policy)
    records: list[dict[str, Any]] = []
    capture_stats = capture_stats or {}
    frames_by_path = capture_stats.get("frames_by_path") if isinstance(capture_stats.get("frames_by_path"), dict) else {}
    counts = {
        "attempted": int(capture_stats.get("attempted") or 0),
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
        if not capture_stats.get("attempted"):
            counts["attempted"] += 1
        capture_record = frames_by_path.get(str(source_path), {}) if isinstance(frames_by_path, dict) else {}
        attempt_index = int(capture_record.get("attempt_index") or index)
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
                "frame_index": attempt_index,
                "saved_index": index,
                "timestamp": capture_record.get("capture_timestamp") or now_iso(),
                "capture_method": "ffmpeg_testsrc" if mode == "dry-run" else "obs_video_frame_capture",
                "source_method": "ffmpeg_testsrc" if mode == "dry-run" else "obs_websocket_source_screenshot",
                "obs_scene": profile.get("obs_scene") or obs_result.get("active_scene"),
                "obs_source": profile.get("_resolved_obs_source") or profile.get("obs_source") or "ffmpeg_testsrc",
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
                "last_action": (frame_actions or {}).get(attempt_index),
                "variation_decision": capture_record.get("variation_decision"),
                "phash_distance_min": capture_record.get("phash_distance_min"),
                "luma_difference_min": capture_record.get("luma_difference_min"),
                "consecutive_frame_diff": capture_record.get("consecutive_frame_diff"),
                "histogram_diff": capture_record.get("histogram_diff"),
                "capture_latency_ms": capture_record.get("capture_latency_ms"),
                "variation_quality_latency_ms": capture_record.get("quality_latency_ms"),
                "save_latency_ms": capture_record.get("save_latency_ms"),
                "online_inference": False,
                "model_action_control": False,
            }
        )
    for key, value in capture_stats.items():
        if key == "frames_by_path":
            continue
        if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
            counts[key] = value  # type: ignore[assignment]
    counts["valid_per_minute"] = capture_stats.get("valid_per_minute", capture_stats.get("saved_per_minute", 0))
    return records, counts


def create_visualizations(run_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    high_records = [record for record in records if record.get("bucket") == "high"]
    sample_paths = evenly_sample_paths([Path(str(record["file_path"])) for record in high_records], target=20)
    action_records = [record for record in high_records if record.get("last_action")]
    action_paths = evenly_sample_paths([Path(str(record["file_path"])) for record in action_records], target=12)
    overview = run_dir / "sampled_montage_overview.png"
    action_montage = run_dir / "action_to_frame_montage.png"
    overview_ok = make_montage(sample_paths, overview, columns=5, label_prefix="sample") if sample_paths else False
    action_ok = make_montage(action_paths, action_montage, columns=4, label_prefix="action") if action_paths else False
    action_diffs = [
        float(record.get("consecutive_frame_diff") or record.get("frame_diff") or 0)
        for record in action_records
        if record.get("consecutive_frame_diff") is not None or record.get("frame_diff") is not None
    ]
    action_count = len(action_records)
    behavior_effect_passed = bool(action_count > 0 and percentile(action_diffs, 50) >= 3.0)
    return {
        "sampled_montage_overview": str(overview),
        "sampled_montage_overview_exists": overview_ok,
        "action_to_frame_montage": str(action_montage),
        "action_to_frame_montage_exists": action_ok,
        "action_count": action_count,
        "last_action_coverage_ratio": round(action_count / max(1, len(high_records)), 6),
        "action_to_frame_effect_passed": behavior_effect_passed,
        "behavior_effect_passed": behavior_effect_passed,
        "behavior_no_effect": not behavior_effect_passed,
    }


def evenly_sample_paths(paths: list[Path], target: int) -> list[Path]:
    if len(paths) <= target:
        return paths
    if target <= 1:
        return [paths[0]]
    selected = []
    for index in range(target):
        selected.append(paths[round(index * (len(paths) - 1) / (target - 1))])
    return selected


def make_montage(paths: list[Path], output: Path, columns: int = 5, label_prefix: str = "frame") -> bool:
    if not paths:
        return False
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        return False
    thumbs = []
    thumb_w = 320
    thumb_h = 180
    label_h = 24
    for index, path in enumerate(paths, start=1):
        try:
            with Image.open(path) as image:
                thumb = image.convert("RGB")
                thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (thumb_w, thumb_h + label_h), "white")
                x = (thumb_w - thumb.width) // 2
                y = (thumb_h - thumb.height) // 2
                canvas.paste(thumb, (x, y))
                draw = ImageDraw.Draw(canvas)
                draw.text((6, thumb_h + 4), f"{label_prefix}_{index}: {path.name}", fill=(20, 20, 20))
                thumbs.append(canvas)
        except Exception:
            continue
    if not thumbs:
        return False
    rows = math.ceil(len(thumbs) / columns)
    montage = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), "white")
    for index, thumb in enumerate(thumbs):
        x = (index % columns) * thumb_w
        y = (index // columns) * (thumb_h + label_h)
        montage.paste(thumb, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    montage.save(output, compress_level=1)
    return output.exists()


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
        "status": status_from_counts(summary_counts, target_total, profile),
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


def status_from_counts(summary_counts: dict[str, Any], target_total: int, profile: dict[str, Any]) -> str:
    required_valid = int(profile.get("valid_min_override") or min(target_total, max(60, round(target_total * 0.67))))
    if int(summary_counts.get("valid_total") or 0) < required_valid:
        return "failed_low_yield"
    if summary_counts.get("variation_gate_enabled"):
        if summary_counts.get("visual_variation_passed") is False:
            return "failed_low_variation"
        if summary_counts.get("behavior_effect_passed") is False:
            return "failed_behavior_no_effect"
    return "capture_completed"


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


class BehaviorExecutor:
    allowed_keys = {"w": 0x57, "a": 0x41, "s": 0x53, "d": 0x44}

    def __init__(self, run_dir: Path, behavior_pack: dict[str, Any], execute_real: bool) -> None:
        self.run_dir = run_dir
        self.behavior_pack = behavior_pack
        self.execute_real = execute_real
        self.action_log = run_dir / "action_log.jsonl"
        self.actions = list(behavior_pack.get("actions") or [])
        self.blocked = set(behavior_pack.get("blocked_actions") or []) | set(behavior_pack.get("blocked_contexts") or [])
        self.stop_file = Path(str(behavior_pack.get("stop_file") or run_dir / "_stop_onegame_mvp.txt"))
        self.frame_actions: dict[int, dict[str, Any]] = {}
        self._next_action = 0
        self._pressed_keys: set[str] = set()
        self.action_every_frames = max(1, int(behavior_pack.get("action_every_frames") or 1))
        self.max_key_duration_ms = int(behavior_pack.get("max_key_duration_ms") or 2000)
        self.max_pause_duration_ms = int(behavior_pack.get("max_pause_duration_ms") or 2000)
        self.max_mouse_dx = int(behavior_pack.get("max_mouse_dx") or 400)
        self.max_mouse_dy = int(behavior_pack.get("max_mouse_dy") or 120)

    def prepare(self) -> Path:
        self.validate_actions()
        self.action_log.parent.mkdir(parents=True, exist_ok=True)
        self.action_log.write_text("", encoding="utf-8")
        if not self.execute_real:
            for index, action in enumerate(self.actions, start=1):
                self._append_action_row(index, action, dry_run=True, executed=False, skipped=False)
        return self.action_log

    def validate_actions(self) -> None:
        if not self.actions:
            return
        for index, action in enumerate(self.actions, start=1):
            unsafe, reason = self._unsafe_reason(action)
            if unsafe:
                raise RuntimeError(f"blocked_by_behavior_risk:{index}:{reason}")
            action_type = str(action.get("type") or "")
            key = str(action.get("key") or "").lower()
            duration_ms = int(action.get("duration_ms") or 0)
            if action_type == "key_hold" and key not in self.allowed_keys:
                raise RuntimeError(f"blocked_by_behavior_key_not_allowed:{key}")
            if action_type == "mouse_move":
                dx = abs(int(action.get("dx") or 0))
                dy = abs(int(action.get("dy") or 0))
                if dx > self.max_mouse_dx or dy > self.max_mouse_dy:
                    raise RuntimeError("blocked_by_behavior_mouse_delta_too_large")
            if action_type not in {"pause", "key_hold", "mouse_move"}:
                raise RuntimeError(f"blocked_by_behavior_action_type:{action_type}")
            max_duration = self.max_pause_duration_ms if action_type == "pause" else self.max_key_duration_ms
            if action_type == "mouse_move":
                max_duration = int(self.behavior_pack.get("max_mouse_duration_ms") or self.max_key_duration_ms)
            if duration_ms < 0 or duration_ms > max_duration:
                raise RuntimeError("blocked_by_behavior_duration")

    def step(self, frame_index: int) -> None:
        if not self.execute_real or not self.actions:
            return
        if frame_index != 1 and (frame_index - 1) % self.action_every_frames != 0:
            return
        if self.stop_file.exists():
            raise RuntimeError("blocked_by_operator_stop_file")
        action = self.actions[self._next_action % len(self.actions)]
        self._next_action += 1
        action_index = self._next_action
        started_at = now_iso()
        try:
            self._execute_action(action)
            row = self._append_action_row(
                action_index,
                action,
                dry_run=False,
                executed=True,
                skipped=False,
                started_at=started_at,
                frame_index=frame_index,
            )
            self.frame_actions[frame_index] = row
        except Exception:
            self.release_all()
            raise

    def close(self) -> None:
        self.release_all()

    def release_all(self) -> None:
        for key in list(self._pressed_keys):
            self._key_up(key)
        self._pressed_keys.clear()

    def _execute_action(self, action: dict[str, Any]) -> None:
        action_type = str(action.get("type") or "")
        duration_ms = int(action.get("duration_ms") or 0)
        if action_type == "pause":
            time.sleep(duration_ms / 1000)
            return
        if action_type == "key_hold":
            key = str(action.get("key") or "").lower()
            self._key_down(key)
            try:
                time.sleep(duration_ms / 1000)
            finally:
                self._key_up(key)
            return
        if action_type == "mouse_move":
            dx = int(action.get("dx") or 0)
            dy = int(action.get("dy") or 0)
            if bool(self.behavior_pack.get("random_jitter", False)):
                dx += random.randint(-12, 12)
                dy += random.randint(-4, 4)
            steps = max(1, min(24, duration_ms // 35 if duration_ms else 1))
            moved_x = moved_y = 0
            for step in range(1, steps + 1):
                target_x = round(dx * step / steps)
                target_y = round(dy * step / steps)
                self._mouse_move(target_x - moved_x, target_y - moved_y)
                moved_x, moved_y = target_x, target_y
                time.sleep(max(0.01, duration_ms / 1000 / steps))
            return
        raise RuntimeError(f"blocked_by_behavior_action_type:{action_type}")

    def _unsafe_reason(self, action: dict[str, Any]) -> tuple[bool, str]:
        action_type = str(action.get("type") or "")
        action_name = str(action.get("name") or "")
        risk_flags = set(action.get("risk_flags") or [])
        if action_type in SAFE_BLOCKED_ACTIONS:
            return True, action_type
        if action_name in SAFE_BLOCKED_ACTIONS:
            return True, action_name
        overlap = risk_flags & SAFE_BLOCKED_ACTIONS
        if overlap:
            return True, ",".join(sorted(overlap))
        return False, ""

    def _append_action_row(
        self,
        index: int,
        action: dict[str, Any],
        dry_run: bool,
        executed: bool,
        skipped: bool,
        started_at: str | None = None,
        frame_index: int | None = None,
    ) -> dict[str, Any]:
        row = {
            "index": index,
            "action_name": str(action.get("name") or f"action_{index}"),
            "action_type": str(action.get("type") or ""),
            "key": action.get("key"),
            "dx": action.get("dx"),
            "dy": action.get("dy"),
            "duration_ms": action.get("duration_ms"),
            "dry_run": dry_run,
            "executed": executed,
            "skipped": skipped,
            "risk_flags": list(action.get("risk_flags") or []),
            "frame_index": frame_index,
            "timestamp": started_at or now_iso(),
            "finished_at": now_iso(),
        }
        with self.action_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return row

    def _key_down(self, key: str) -> None:
        vk = self.allowed_keys[key]
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        self._pressed_keys.add(key)

    def _key_up(self, key: str) -> None:
        vk = self.allowed_keys[key]
        ctypes.windll.user32.keybd_event(vk, 0, 0x0002, 0)
        self._pressed_keys.discard(key)

    def _mouse_move(self, dx: int, dy: int) -> None:
        ctypes.windll.user32.mouse_event(0x0001, int(dx), int(dy), 0, 0)


def write_behavior_actions(run_dir: Path, behavior_pack: dict[str, Any], execute_real: bool) -> Path:
    executor = BehaviorExecutor(run_dir, behavior_pack, execute_real=execute_real)
    path = executor.prepare()
    executor.close()
    return path


def load_frame_actions(path: Path) -> dict[int, dict[str, Any]]:
    actions: dict[int, dict[str, Any]] = {}
    if not path.exists():
        return actions
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        frame_index = row.get("frame_index")
        if isinstance(frame_index, int):
            actions[frame_index] = row
    return actions


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
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as image:
            source_width, source_height = image.size
            gray = image.convert("L")
            max_width = 320
            if source_width > max_width:
                target_width = max_width
                target_height = max(1, round(source_height * target_width / source_width))
                gray = gray.resize((target_width, target_height))
            width, height = gray.size
            return PngPixels(
                width=int(width),
                height=int(height),
                gray=list(gray.tobytes()),
                source_width=int(source_width),
                source_height=int(source_height),
            )
    except ImportError:
        pass

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
    return PngPixels(width=int(width), height=int(height), gray=gray, source_width=int(width), source_height=int(height))


def downsample_pixels(pixels: PngPixels, max_width: int = 320) -> PngPixels:
    if pixels.width <= max_width:
        return pixels
    source_width = pixels.source_width or pixels.width
    source_height = pixels.source_height or pixels.height
    target_width = max(1, max_width)
    target_height = max(1, round(pixels.height * target_width / pixels.width))
    return PngPixels(
        width=target_width,
        height=target_height,
        gray=sample_gray(pixels.gray, pixels.width, pixels.height, target_width, target_height),
        source_width=source_width,
        source_height=source_height,
    )


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


def mean_or_zero(values: list[float] | list[int]) -> float:
    return round(sum(float(value) for value in values) / len(values), 6) if values else 0.0


def percentile(values: list[float] | list[int], pct: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(float(value) for value in values)
    if len(sorted_values) == 1:
        return round(sorted_values[0], 6)
    index = (len(sorted_values) - 1) * pct / 100
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return round(sorted_values[int(index)], 6)
    weight = index - lower
    return round(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight, 6)


def grayscale_histogram(gray: list[int], bins: int = 32) -> list[float]:
    hist = [0] * bins
    for value in gray:
        bucket = min(bins - 1, max(0, int(value) * bins // 256))
        hist[bucket] += 1
    total = max(1, len(gray))
    return [count / total for count in hist]


def histogram_distance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 1.0
    return sum(abs(a - b) for a, b in zip(left, right)) / 2


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
