from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from ai_screenshot_platform.v3.capture.folder_watch import list_new_images
from ai_screenshot_platform.v3.capture.obs_websocket import config_from_payload, list_scenes, list_sources, obs_status, take_obs_screenshot
from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.action.input_gateway import load_input_gateway_readiness
from ai_screenshot_platform.v3.action.rollback import rollback_plan
from ai_screenshot_platform.v3.action.action_loop import ActionLoop
from ai_screenshot_platform.v3.action.candidate_fusion import fuse_candidates
from ai_screenshot_platform.v3.action.candidate_generator import ocr_candidates
from ai_screenshot_platform.v3.action.safety_gate import risk_terms_in_text
from ai_screenshot_platform.v3.model.health import build_v3_health
from ai_screenshot_platform.v3.model.registry import UiModelRegistry
from ai_screenshot_platform.v3.model.showui_provider import preload_showui_torch_runtime
from ai_screenshot_platform.v3.ocr.language_filter import filter_language
from ai_screenshot_platform.v3.ocr.mock_provider import MockOcrProvider
from ai_screenshot_platform.v3.ocr.paddle_provider import PaddleOcrProvider
from ai_screenshot_platform.v3.quality.duplicate_filter import DuplicateFilter
from ai_screenshot_platform.v3.quality.image_quality import basic_image_quality
from ai_screenshot_platform.v3.schemas import (
    ModelRequest,
    OcrResult,
    V3CollectionExportResult,
    V3CollectionRecord,
    V3CollectionSummary,
    V3DeleteResult,
    V3FramePumpStartRequest,
    V3FramePumpStatus,
    V3Health,
    V3ImageRecord,
    V3InputStatus,
    V3ObsConfigRequest,
    V3RunRecord,
    V3Summary,
    V3TaskConfig,
    utc_now,
)
from ai_screenshot_platform.v3.storage.run_store import V3RunStore


class V3Runtime:
    def __init__(
        self,
        store: V3RunStore | None = None,
        model_registry: UiModelRegistry | None = None,
        ocr_provider: OcrProvider | None = None,
        action_loop: ActionLoop | None = None,
    ) -> None:
        self.store = store or V3RunStore()
        self.model_registry = model_registry or UiModelRegistry()
        self.mock_ocr = MockOcrProvider()
        preload_showui_torch_runtime()
        self.paddle_ocr = PaddleOcrProvider()
        self.ocr_provider = ocr_provider
        self.duplicates = DuplicateFilter()
        self.actions = action_loop or ActionLoop()
        self._action_duplicate_preserve_counts: dict[tuple[str, str, str], int] = {}
        self._ocr_by_sha: dict[str, OcrResult] = {}
        self._duplicate_seen_by_sha: dict[str, dict[str, str]] = {}
        self._watch_threads: dict[str, threading.Thread] = {}
        self._watch_seen: dict[str, set[str]] = {}
        self._watch_waiting_since: dict[str, float] = {}

    def health(self) -> V3Health:
        return build_v3_health(self.model_registry)

    def action_health(self) -> dict[str, object]:
        return load_input_gateway_readiness().model_dump()

    def defaults(self) -> V3TaskConfig:
        return V3TaskConfig()

    def create_collection(self, config: V3TaskConfig) -> V3CollectionRecord:
        return self.store.create_collection(config)

    def list_collections(self) -> list[V3CollectionRecord]:
        return self.store.list_collections()

    def get_collection(self, collection_id: str) -> V3CollectionRecord:
        return self.store.get_collection(collection_id)

    def collection_summary(self, collection_id: str) -> V3CollectionSummary:
        return self.store.refresh_collection_summary(collection_id)

    def collection_gallery(self, collection_id: str) -> list[V3ImageRecord]:
        return self.store.collection_images(collection_id, unique_only=True)

    def continue_collection(self, collection_id: str) -> V3RunRecord:
        return self.store.continue_collection(collection_id)

    def stop_collection(self, collection_id: str) -> V3CollectionRecord:
        collection = self.store.stop_collection(collection_id)
        active_statuses = {"running", "waiting_for_input", "waiting_for_input_timeout"}
        has_other_active_collection = any(
            bool(run.collection_id) and run.collection_id != collection_id and run.status in active_statuses
            for run in self.list_runs()
        )
        if not has_other_active_collection:
            self.stop_frame_pump()
        self._watch_waiting_since.pop(collection.latest_run_id or "", None)
        return collection

    def export_collection(self, collection_id: str) -> V3CollectionExportResult:
        return self.store.export_collection(collection_id)

    def delete_collection(self, collection_id: str, delete_files: bool = False) -> V3DeleteResult:
        try:
            result = self.store.delete_collection(collection_id, delete_files=delete_files)
        except ValueError as exc:
            if str(exc) == "collection_has_running_run":
                raise RuntimeError("采集项目仍有运行中的轮次，请先停止采集再删除。") from exc
            raise
        return V3DeleteResult.model_validate(result)

    def restore_collection(self, collection_id: str) -> V3CollectionRecord:
        return self.store.restore_collection(collection_id)

    def delete_run(self, run_id: str, delete_files: bool = False) -> V3DeleteResult:
        try:
            result = self.store.delete_run(run_id, delete_files=delete_files)
        except ValueError as exc:
            if str(exc) == "run_is_running":
                raise RuntimeError("该轮次仍在运行，请先停止再删除。") from exc
            raise
        return V3DeleteResult.model_validate(result)

    def create_run(self, config: V3TaskConfig, collection_id: str | None = None) -> V3RunRecord:
        return self.store.create_run(config, collection_id=collection_id)

    def list_runs(self) -> list[V3RunRecord]:
        return self.store.list_runs()

    def get_run(self, run_id: str) -> V3RunRecord:
        return self.store.get_run(run_id)

    def start_run(self, run_id: str) -> V3RunRecord:
        record = self.get_run(run_id)
        if os.environ.get("APP_SHOT_DISABLE_FRAME_PUMP") != "1" and self.frame_pump_status().status != "running":
            self.start_frame_pump(self._frame_pump_request_for_config(record.config))
        watch_dir = self._watch_dir()
        watch_dir.mkdir(parents=True, exist_ok=True)
        self._watch_seen[run_id] = {str(path.resolve()) for path in list_new_images(watch_dir)}
        input_status = self.input_status()
        status = "waiting_for_input" if input_status.status in {"waiting_for_input", "stale"} else "running"
        record = self.store.update_status(run_id, status)
        self.store.append_event(
            run_id,
            "run_started",
            {"observe_only": record.config.observe_only, "watch_dir": str(watch_dir), "input_status": input_status.model_dump()},
        )
        self._ensure_watch_thread(run_id)
        return record

    def pause_run(self, run_id: str) -> V3RunRecord:
        record = self.store.update_status(run_id, "paused")
        self.store.append_event(run_id, "run_paused", {})
        return record

    def resume_run(self, run_id: str) -> V3RunRecord:
        if os.environ.get("APP_SHOT_DISABLE_FRAME_PUMP") != "1" and self.frame_pump_status().status != "running":
            self.start_frame_pump(self._frame_pump_request_for_config(record.config))
        record = self.store.update_status(run_id, "waiting_for_input")
        self.store.append_event(run_id, "run_resumed", {})
        self._ensure_watch_thread(run_id)
        return record

    def stop_run(self, run_id: str) -> V3RunRecord:
        record = self.store.update_status(run_id, "stopped")
        self.store.append_event(run_id, "run_stopped", {})
        return record

    def run_status(self, run_id: str) -> dict[str, object]:
        record = self.get_run(run_id)
        summary = self.summary(run_id)
        input_status = self.input_status()
        return {
            "run": record.model_dump(),
            "summary": summary.model_dump(),
            "input_status": input_status.model_dump(),
        }

    def frame_pump_status(self) -> V3FramePumpStatus:
        output_dir = self._watch_dir()
        heartbeat = self._frame_pump_heartbeat_path()
        pid_file = self._frame_pump_pid_path()
        pid = _read_int(pid_file)
        running = bool(pid and _process_exists(pid))
        latest = _latest_image(output_dir)
        seconds_since_latest = None
        latest_time = None
        if latest:
            seconds_since_latest = max(0.0, time.time() - latest.stat().st_mtime)
            latest_time = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(latest.stat().st_mtime))
        frame_count = len(list_new_images(output_dir)) if output_dir.exists() else 0
        heartbeat_payload: dict[str, object] = {}
        if heartbeat.is_file():
            try:
                payload = json.loads(heartbeat.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    heartbeat_payload = payload
            except json.JSONDecodeError:
                heartbeat_payload = {}
        error = str(heartbeat_payload.get("error") or "") or None
        heartbeat_status = str(heartbeat_payload.get("status") or "")
        if heartbeat_status == "stopped":
            running = False
            pid_file.unlink(missing_ok=True)
            pid = None
        fps = heartbeat_payload.get("fps")
        mode = str(heartbeat_payload.get("mode") or "fullscreen")
        source_mode = str(heartbeat_payload.get("source_mode") or mode or "screen")
        obs_connected = bool(heartbeat_payload.get("obs_connected"))
        obs_scene_name = heartbeat_payload.get("obs_scene_name")
        obs_source_name = heartbeat_payload.get("obs_source_name")
        if error:
            status = "error"
            message = f"Frame Pump 异常：{error}"
        elif running and seconds_since_latest is not None and seconds_since_latest <= 30:
            status = "running"
            message = "Frame Pump 正在输出截图。"
        elif running:
            status = "stale"
            message = "Frame Pump 进程存在，但 30 秒内没有新截图。"
        else:
            status = "stopped"
            message = "Frame Pump 未运行。"
        return V3FramePumpStatus(
            status=status,  # type: ignore[arg-type]
            output_dir=str(output_dir),
            pid=pid if running else None,
            latest_frame=latest.name if latest else None,
            latest_frame_path=str(latest) if latest else None,
            latest_frame_time=latest_time,
            seconds_since_latest=round(seconds_since_latest, 1) if seconds_since_latest is not None else None,
            frame_count=frame_count,
            fps=float(fps) if isinstance(fps, (int, float)) else None,
            mode=mode,
            message=message,
            heartbeat_path=str(heartbeat),
            error=error,
            source_mode=source_mode,
            obs_connected=obs_connected,
            obs_scene_name=str(obs_scene_name) if obs_scene_name else None,
            obs_source_name=str(obs_source_name) if obs_source_name else None,
        )

    def start_frame_pump(self, request: V3FramePumpStartRequest | None = None) -> V3FramePumpStatus:
        request = request or V3FramePumpStartRequest()
        if os.environ.get("APP_SHOT_DISABLE_FRAME_PUMP") == "1":
            status = self.frame_pump_status()
            status.message = "Frame Pump disabled by APP_SHOT_DISABLE_FRAME_PUMP"
            return status
        status = self.frame_pump_status()
        if status.status == "running":
            return status
        output_dir = self._watch_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        stop_file = self._frame_pump_stop_path()
        stop_file.unlink(missing_ok=True)
        pid_file = self._frame_pump_pid_path()
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        heartbeat = self._frame_pump_heartbeat_path()
        heartbeat.parent.mkdir(parents=True, exist_ok=True)
        heartbeat.unlink(missing_ok=True)
        self._frame_pump_status_path().unlink(missing_ok=True)
        pid_file.unlink(missing_ok=True)
        args = [
            sys.executable,
            "-m",
            "ai_screenshot_platform.v3.capture.frame_pump",
            "--output-dir",
            str(output_dir),
            "--heartbeat-path",
            str(heartbeat),
            "--stop-file",
            str(stop_file),
            "--fps",
            str(request.fps),
            "--source-mode",
            request.source_mode,
            "--obs-host",
            request.obs_host,
            "--obs-port",
            str(request.obs_port),
            "--screenshot-target",
            request.screenshot_target,
            "--image-format",
            request.image_format,
            "--image-quality",
            str(request.image_quality),
            "--status-path",
            str(self._frame_pump_status_path()),
        ]
        password = request.obs_password if request.obs_password is not None else os.environ.get("APP_SHOT_OBS_PASSWORD", "")
        if password:
            args.extend(["--obs-password", password])
        if request.obs_scene_name:
            args.extend(["--obs-scene-name", request.obs_scene_name])
        if request.obs_source_name:
            args.extend(["--obs-source-name", request.obs_source_name])
        if request.full_screen:
            args.append("--full-screen")
        if request.window_title:
            args.extend(["--window-title", request.window_title])
        env = os.environ.copy()
        src_root = Path(__file__).resolve().parents[2]
        env["PYTHONPATH"] = str(src_root) + os.pathsep + env.get("PYTHONPATH", "")
        process = subprocess.Popen(args, cwd=str(src_root.parent), env=env)
        pid_file.write_text(str(process.pid), encoding="utf-8")
        time.sleep(0.2)
        return self.frame_pump_status()

    def obs_status(self, request: V3ObsConfigRequest | None = None) -> dict[str, object]:
        return obs_status(config_from_payload(request.model_dump() if request else None))

    def obs_scenes(self, request: V3ObsConfigRequest | None = None) -> dict[str, object]:
        return list_scenes(config_from_payload(request.model_dump() if request else None))

    def obs_sources(self, request: V3ObsConfigRequest | None = None, scene_name: str | None = None) -> dict[str, object]:
        return list_sources(config_from_payload(request.model_dump() if request else None), scene_name=scene_name)

    def obs_test_screenshot(self, request: V3ObsConfigRequest | None = None) -> dict[str, object]:
        config = config_from_payload(request.model_dump() if request else None)
        try:
            return take_obs_screenshot(config, self._watch_dir(), frame_index=int(time.time()))
        except Exception as exc:
            return {
                "ok": False,
                "image_path": None,
                "width": None,
                "height": None,
                "source_mode": "obs_websocket",
                "black_screen_detected": False,
                "message": str(exc),
            }

    def frame_pump_test_shot(self, request: V3FramePumpStartRequest | None = None) -> dict[str, object]:
        request = request or V3FramePumpStartRequest()
        if request.source_mode == "obs_websocket":
            obs_request = V3ObsConfigRequest(
                obs_host=request.obs_host,
                obs_port=request.obs_port,
                obs_password=request.obs_password,
                obs_scene_name=request.obs_scene_name,
                obs_source_name=request.obs_source_name,
                screenshot_target=request.screenshot_target,
                image_format=request.image_format,
                image_quality=request.image_quality,
            )
            return self.obs_test_screenshot(obs_request)
        from PIL import ImageGrab

        self._watch_dir().mkdir(parents=True, exist_ok=True)
        image = ImageGrab.grab(all_screens=request.full_screen)
        frame_path = self._watch_dir() / f"frame_{time.strftime('%Y%m%d_%H%M%S')}_test_{request.source_mode}.png"
        image.save(frame_path)
        return {"ok": True, "image_path": str(frame_path), "width": image.width, "height": image.height, "source_mode": request.source_mode}

    def stop_frame_pump(self) -> V3FramePumpStatus:
        self._frame_pump_stop_path().write_text(utc_now(), encoding="utf-8")
        pid = _read_int(self._frame_pump_pid_path())
        deadline = time.time() + 3.0
        while pid and _process_exists(pid) and time.time() < deadline:
            time.sleep(0.1)
        heartbeat_status = ""
        heartbeat = self._frame_pump_heartbeat_path()
        if heartbeat.is_file():
            try:
                payload = json.loads(heartbeat.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    heartbeat_status = str(payload.get("status") or "")
            except json.JSONDecodeError:
                heartbeat_status = ""
        if heartbeat_status == "stopped" or (pid and not _process_exists(pid)):
            self._frame_pump_pid_path().unlink(missing_ok=True)
        return self.frame_pump_status()

    def summary(self, run_id: str) -> V3Summary:
        health = self.health()
        ocr_ready = any(item.status == "ready" for item in health.ocr)
        model_ready = any(item.provider == "showui" and item.status == "ready" and item.enabled for item in health.models)
        summary = self.store.summary(
            run_id,
            ocr_ready=ocr_ready,
            model_ready=model_ready,
            safety_gate_ready=True,
            ocr_gpu_ready=health.ocr_gpu_ready,
            ocr_performance_ready=health.ocr_performance_ready,
            ocr_production_ready=health.ocr_production_ready,
            input_gateway_ready=health.input_gateway_ready,
            cursor_read_ready=health.cursor_read_ready,
            mouse_click_ready=health.mouse_click_ready,
            same_desktop_session_ready=health.same_desktop_session_ready,
            same_integrity_ready=health.same_integrity_ready,
            interactive_desktop_ready=health.interactive_desktop_ready,
            click_backend=health.click_backend,
            input_gateway_blockers=health.input_gateway_blockers,
            readiness_blockers=health.readiness_blockers,
        )
        summary.input_status = self.input_status()
        summary.status = self._derived_status(self.get_run(run_id), summary, summary.input_status)
        return summary

    def input_status(self) -> V3InputStatus:
        watch_dir = self._watch_dir()
        if not watch_dir.exists():
            return V3InputStatus(
                watch_dir=str(watch_dir),
                exists=False,
                status="path_missing",
                message=f"OBS 输出目录不存在：{watch_dir}",
            )
        try:
            images = list_new_images(watch_dir)
        except Exception as exc:
            return V3InputStatus(
                watch_dir=str(watch_dir),
                exists=True,
                status="unreadable",
                message=f"OBS 输出目录无法读取：{exc}",
            )
        if not images:
            return V3InputStatus(
                watch_dir=str(watch_dir),
                exists=True,
                status="waiting_for_input",
                message=f"正在等待 OBS 输出截图，请确认 OBS 已启动，并且输出目录为 {watch_dir}。",
            )
        latest = max(images, key=lambda item: item.stat().st_mtime)
        latest_time = latest.stat().st_mtime
        seconds = max(0.0, time.time() - latest_time)
        status = "receiving" if seconds <= 10 else "stale"
        message = "正常接收 OBS 截图。" if status == "receiving" else "长时间未收到新的 OBS 截图。"
        return V3InputStatus(
            watch_dir=str(watch_dir),
            exists=True,
            latest_file=latest.name,
            latest_file_path=str(latest),
            latest_file_time=time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(latest_time)),
            seconds_since_latest=round(seconds, 1),
            status=status,
            message=message,
        )

    def images(self, run_id: str) -> list[V3ImageRecord]:
        return self.store.list_images(run_id)

    def events(self, run_id: str):
        return self.store.list_events(run_id)

    def ingest_image(
        self,
        run_id: str,
        image_path: str,
        capture_reason: str = "periodic",
        action_id: str | None = None,
        ui_state_hint: str = "unknown",
    ) -> V3ImageRecord:
        record = self.get_run(run_id)
        path = Path(image_path)
        quality = basic_image_quality(path)
        unique = False
        digest: str | None = _file_sha256(str(path))
        if quality["accepted"]:
            unique, digest = self.duplicates.check(path)
        compared_with = self._duplicate_seen_by_sha.get(digest or "")
        existing_images = self.store.list_images(run_id)
        existing_state_count = sum(
            1
            for image in existing_images
            if image.bucket == "accepted" and str(image.meta.get("ui_state_hint") or "unknown") == ui_state_hint
        )
        bucket = "pending"
        reject_reason = None
        if not quality["accepted"]:
            bucket = "rejected"
            reject_reason = str(quality["reason"])
        duplicate_preserved = False
        representative_limit = 3
        representative_group_key = f"{action_id}|{ui_state_hint}" if action_id else None
        representative_index = None
        if action_id and capture_reason in {"before_action", "after_action", "rollback_after", "menu_state", "dialog_state"}:
            key = (run_id, str(action_id), ui_state_hint)
            representative_index = self._action_duplicate_preserve_counts.get(key, 0) + 1
        if quality["accepted"] and not unique:
            duplicate_preserved = self._should_preserve_action_duplicate(run_id, capture_reason, action_id, ui_state_hint)
        if not quality["accepted"]:
            bucket = "rejected"
            reject_reason = str(quality["reason"])
        elif not unique and not duplicate_preserved:
            bucket = "rejected"
            reject_reason = "near_duplicate"
        meta: dict[str, object] = {
            "capture_source": record.config.capture_source,
            "capture_reason": capture_reason,
            "action_id": action_id,
            "ui_state_hint": ui_state_hint,
            "duplicate_preserved": duplicate_preserved,
            "quality": quality,
        }
        ocr_cache_hit = False
        if bucket == "pending" and record.config.enable_ocr:
            if duplicate_preserved and digest and digest in self._ocr_by_sha:
                ocr_result = self._ocr_by_sha[digest]
                ocr_cache_hit = True
            else:
                ocr_result = self._recognize_for_target(str(path), record.config.target_language)
                if digest and ocr_result.status == "ok":
                    self._ocr_by_sha[digest] = ocr_result
            meta["ocr"] = ocr_result.model_dump()
            self.store.append_meta_jsonl(run_id, "ocr.jsonl", meta["ocr"])
            if ocr_result.status != "ok":
                bucket = "manual_review"
                reject_reason = ocr_result.error or ocr_result.status
            else:
                language_evaluations = []
                for box in ocr_result.text_boxes:
                    result = filter_language(box.text, record.config.target_language)
                    if not result.accepted and _is_low_confidence_short_noise(box.text, box.confidence):
                        continue
                    language_evaluations.append((box, result))
                accepted_boxes = [box for box, result in language_evaluations if result.accepted]
                rejected_language_results = [
                    result
                    for _, result in language_evaluations
                    if result.reason in {"wrong_language", "mixed_language"}
                ]
                risk_hits = sorted({risk for box in accepted_boxes for risk in risk_terms_in_text(box.text)})
                safe_accepted_boxes = [box for box in accepted_boxes if not risk_terms_in_text(box.text)]
                if accepted_boxes and risk_hits and not safe_accepted_boxes:
                    bucket = "rejected"
                    reject_reason = "unsafe_text"
                    meta["risk_hits"] = risk_hits
                elif accepted_boxes and max((box.confidence for box in safe_accepted_boxes or accepted_boxes), default=0.0) < 0.5:
                    bucket = "rejected"
                    reject_reason = "low_ocr_confidence"
                elif accepted_boxes:
                    if rejected_language_results and not _pc_app_target_language_dominates(
                        record.config.app_type,
                        ocr_result.text_boxes,
                        record.config.target_language,
                    ):
                        bucket = "rejected"
                        reject_reason = "mixed_language"
                    else:
                        bucket = "accepted"
                        meta["accepted_class"] = _accepted_text_class(record.config.app_type, ui_state_hint)
                elif record.config.must_have_text and not ocr_result.text_boxes:
                    bucket, reject_reason = self._no_text_decision(record, existing_images)
                    if bucket == "accepted":
                        meta["accepted_class"] = "accepted_visual_fill"
                elif record.config.must_have_text:
                    bucket = "rejected"
                    reject_reason = "wrong_language"
                elif not ocr_result.text_boxes and _uses_no_text_policy(record.config):
                    bucket, reject_reason = self._no_text_decision(record, existing_images)
                    if bucket == "accepted":
                        meta["accepted_class"] = "accepted_visual_fill"
        if bucket == "accepted" and duplicate_preserved:
            self._mark_action_duplicate_preserved(run_id, capture_reason, action_id, ui_state_hint)
        duplicate_decision = _build_duplicate_decision(
            content_hash=digest,
            exact_duplicate=bool(quality["accepted"] and not unique),
            compared_with=compared_with,
            capture_reason=capture_reason,
            ui_state_hint=ui_state_hint,
            action_id=action_id,
            accepted_as_action_representative=bool(bucket == "accepted" and duplicate_preserved),
            representative_group_key=representative_group_key,
            representative_index=representative_index,
            representative_limit=representative_limit,
            bucket=bucket,
            reject_reason=reject_reason,
            ocr_cache_hit=ocr_cache_hit,
            existing_state_count=existing_state_count,
        )
        if (
            bucket == "rejected"
            and reject_reason == "near_duplicate"
            and compared_with
            and compared_with.get("run_id")
            and compared_with.get("run_id") != run_id
            and record.collection_id
        ):
            reject_reason = "rejected_duplicate_across_runs"
            meta["collection_id"] = record.collection_id
            meta["collection_run_id"] = run_id
            meta["collection_round_index"] = record.round_index
            meta["collection_unique"] = False
            meta["duplicate_across_runs"] = True
            meta["duplicate_with_run_id"] = compared_with.get("run_id")
            meta["duplicate_with_image_id"] = compared_with.get("image_id")
            duplicate_decision["duplicate_decision_reason"] = "rejected_duplicate_across_runs"
            duplicate_decision["duplicate_across_runs"] = True
            duplicate_decision["compared_with_run_id"] = compared_with.get("run_id")
        image = V3ImageRecord(
            image_id=path.stem,
            path=str(path),
            bucket=bucket,  # type: ignore[arg-type]
            sha256=digest,
            content_hash=digest,
            valid=bool(quality["accepted"]),
            near_duplicate=bool(quality["accepted"] and not unique),
            duplicate_decision=duplicate_decision,
            reject_reason=reject_reason,
            meta=meta,
        )
        if quality["accepted"] and unique and digest:
            self._duplicate_seen_by_sha[digest] = {
                "run_id": run_id,
                "image_id": image.image_id,
                "path": image.path,
                "capture_reason": capture_reason,
                "action_id": str(action_id or ""),
                "ui_state_hint": ui_state_hint,
            }
        return self.store.add_image(run_id, image)

    def _no_text_decision(self, record: V3RunRecord, existing_images: list[V3ImageRecord]) -> tuple[str, str | None]:
        config = record.config
        if config.text_policy == "visual_gameplay":
            return "accepted", None
        if config.text_policy == "text_priority_with_fill" and config.allow_no_text_fill:
            accepted_count = sum(1 for image in existing_images if image.bucket == "accepted")
            visual_count = sum(
                1
                for image in existing_images
                if image.bucket == "accepted" and image.meta.get("accepted_class") == "accepted_visual_fill"
            )
            allowed = max(1, int(max(accepted_count, config.target_accepted_min) * config.no_text_fill_ratio))
            if visual_count < allowed:
                return "accepted", None
            return "rejected", "rejected_no_text_over_quota"
        return "rejected", "no_text"

    def _watch_dir(self) -> Path:
        explicit = os.environ.get("APP_SHOT_OBS_OUTPUT")
        if explicit:
            return Path(explicit)
        home = os.environ.get("APP_SHOT_HOME")
        if home:
            return Path(home) / "obs-output"
        return Path("obs-output")

    def _frame_pump_root(self) -> Path:
        home = os.environ.get("APP_SHOT_HOME")
        root = Path(home) if home else Path("runs")
        path = root / "cache" / "frame-pump"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _frame_pump_pid_path(self) -> Path:
        return self._frame_pump_root() / "generic_frame_pump.pid"

    def _frame_pump_stop_path(self) -> Path:
        return self._frame_pump_root() / "generic_frame_pump.stop"

    def _frame_pump_heartbeat_path(self) -> Path:
        explicit = os.environ.get("APP_SHOT_FRAME_PUMP_HEARTBEAT")
        if explicit:
            return Path(explicit)
        home = os.environ.get("APP_SHOT_HOME")
        return (Path(home) if home else Path(".")) / "logs" / "frame_pump_heartbeat.json"

    def _frame_pump_status_path(self) -> Path:
        home = os.environ.get("APP_SHOT_HOME")
        return (Path(home) if home else Path(".")) / "logs" / "frame_pump_status.json"

    def _frame_pump_request_for_config(self, config: V3TaskConfig) -> V3FramePumpStartRequest:
        fps = max(0.2, min(10.0, 1000 / max(config.capture_interval_ms, 100)))
        if config.capture_source in {"obs", "obs_websocket"}:
            return V3FramePumpStartRequest(source_mode="obs_websocket", fps=fps)
        if config.capture_source == "window":
            return V3FramePumpStartRequest(source_mode="window", fps=fps, full_screen=False)
        return V3FramePumpStartRequest(source_mode="screen", fps=fps)

    def _ensure_watch_thread(self, run_id: str) -> None:
        thread = self._watch_threads.get(run_id)
        if thread and thread.is_alive():
            return
        thread = threading.Thread(target=self._watch_loop, args=(run_id,), daemon=True)
        self._watch_threads[run_id] = thread
        thread.start()

    def _watch_loop(self, run_id: str) -> None:
        watch_dir = self._watch_dir()
        seen = self._watch_seen.setdefault(run_id, set())
        while True:
            try:
                record = self.get_run(run_id)
            except KeyError:
                return
            if record.status in {"stopped", "completed", "failed"}:
                return
            if record.status == "paused":
                time.sleep(0.5)
                continue
            watch_dir.mkdir(parents=True, exist_ok=True)
            images = list_new_images(watch_dir, seen)
            if not images:
                waiting_since = self._watch_waiting_since.setdefault(run_id, time.monotonic())
                status = "waiting_for_input_timeout" if time.monotonic() - waiting_since >= 30 else "waiting_for_input"
                self._set_status_if_changed(run_id, status)
                self.store.write_artifact(
                    run_id,
                    "meta/folder_watch_summary.json",
                    {
                        "folder": str(watch_dir),
                        "discovered": 0,
                        "processed": self.store.get_run(run_id).counts.get("accepted", 0)
                        + self.store.get_run(run_id).counts.get("rejected", 0)
                        + self.store.get_run(run_id).counts.get("manual_review", 0),
                        "failed": 0,
                        "seen": len(seen),
                        "stopped_reason": status,
                        "last_poll_at": utc_now(),
                        "frame_pump": self.frame_pump_status().model_dump(),
                    },
                )
                time.sleep(max(0.2, record.config.capture_interval_ms / 1000))
                continue
            self._watch_waiting_since.pop(run_id, None)
            self._set_status_if_changed(run_id, "running")
            for image in images:
                seen.add(str(image.resolve()))
                try:
                    self.ingest_image(run_id, str(image))
                except Exception as exc:
                    self.store.append_event(run_id, "image_ingest_failed", {"image": str(image), "error": str(exc)})
            summary = self.summary(run_id)
            if summary.accepted >= record.config.target_accepted_max or summary.processed >= record.config.max_images:
                self.store.update_status(run_id, "completed")
                return
            time.sleep(max(0.2, record.config.capture_interval_ms / 1000))

    def _set_status_if_changed(self, run_id: str, status: str) -> None:
        try:
            record = self.get_run(run_id)
        except KeyError:
            return
        if record.status != status:
            self.store.update_status(run_id, status)

    def _derived_status(self, record: V3RunRecord, summary: V3Summary, input_status: V3InputStatus) -> str:
        if record.status in {"paused", "stopped", "completed", "failed"}:
            return record.status
        if summary.accepted >= record.config.target_accepted_soft:
            return "completed"
        if record.status in {"running", "waiting_for_input", "waiting_for_input_timeout"} and summary.processed == 0 and input_status.status != "receiving":
            return record.status if record.status == "waiting_for_input_timeout" else "waiting_for_input"
        if summary.processed > 0:
            return "running"
        return record.status

    def _should_preserve_action_duplicate(
        self,
        run_id: str,
        capture_reason: str,
        action_id: str | None,
        ui_state_hint: str,
    ) -> bool:
        if capture_reason not in {"before_action", "after_action", "rollback_after", "menu_state", "dialog_state"}:
            return False
        if not action_id:
            return False
        if ui_state_hint in {"unknown", "editor"}:
            return False
        key = (run_id, action_id, ui_state_hint)
        return self._action_duplicate_preserve_counts.get(key, 0) < 3

    def _mark_action_duplicate_preserved(
        self,
        run_id: str,
        capture_reason: str,
        action_id: str | None,
        ui_state_hint: str,
    ) -> None:
        if not self._should_preserve_action_duplicate(run_id, capture_reason, action_id, ui_state_hint):
            return
        key = (run_id, str(action_id), ui_state_hint)
        self._action_duplicate_preserve_counts[key] = self._action_duplicate_preserve_counts.get(key, 0) + 1

    def _recognize_for_target(self, image_path: str, target_language: str):
        provider = self._active_ocr_provider()
        if isinstance(provider, PaddleOcrProvider):
            return provider.recognize_for_language(image_path, target_language)
        return provider.recognize(image_path)

    def _active_ocr_provider(self) -> OcrProvider:
        if self.ocr_provider is not None:
            return self.ocr_provider
        paddle_health = self.paddle_ocr.health()
        if paddle_health.status == "ready" and paddle_health.enabled:
            return self.paddle_ocr
        return self.mock_ocr

    def ocr_status(self, run_id: str) -> dict[str, object]:
        return {"run_id": run_id, "providers": [self.mock_ocr.health().model_dump(), self.paddle_ocr.health().model_dump()]}

    def model_status(self, run_id: str) -> dict[str, object]:
        return {"run_id": run_id, "providers": [item.model_dump() for item in self.model_registry.health()]}

    def candidates(self, run_id: str) -> list[dict[str, object]]:
        record = self.get_run(run_id)
        images = self.images(run_id)
        if not images:
            return []
        return self._candidates_for_image(run_id, record, images[-1])

    def _candidates_for_image(self, run_id: str, record: V3RunRecord, image: V3ImageRecord) -> list[dict[str, object]]:
        if isinstance(image.meta.get("ocr"), dict):
            from ai_screenshot_platform.v3.schemas import OcrResult

            ocr_result = OcrResult.model_validate(image.meta["ocr"])
        else:
            ocr_result = self._active_ocr_provider().recognize(image.path)
        valid_boxes = [
            box
            for box in ocr_result.text_boxes
            if filter_language(box.text, record.config.target_language).accepted
            or record.config.app_type == "game"
            or _is_safe_pc_app_ui_label(record.config.app_type, box.text)
        ]
        valid_boxes.extend(_split_safe_pc_app_menu_boxes(record.config.app_type, ocr_result.text_boxes))
        ocr_clicks = ocr_candidates(valid_boxes)
        model_request = ModelRequest(
            screenshot_path=image.path,
            task_context=record.config.model_dump(),
            ocr_boxes=valid_boxes,
        )
        model_result = self.model_registry.rank_click_candidates(model_request)
        fused = fuse_candidates(ocr_clicks, model_result.candidates)
        fused = [_classify_candidate_region(item, record.config.app_type) for item in fused]
        self.store.write_artifact(run_id, "candidates.json", [item.model_dump() for item in fused])
        return [item.model_dump() for item in fused]

    def actions_for_run(self, run_id: str) -> list[dict[str, object]]:
        return self.execute_action(run_id)

    def list_actions(self, run_id: str) -> list[dict[str, object]]:
        return self.store.list_meta_jsonl(run_id, "actions.jsonl")

    def evaluate_action(self, run_id: str) -> list[dict[str, object]]:
        prepared = self._prepare_controlled_action(run_id)
        if isinstance(prepared, dict):
            self._write_action_audit(run_id, prepared)
            return [prepared]

        record, latest, selected, executed_count = prepared
        decision = self.actions.safety_gate.evaluate(
            "click",
            candidate=selected,
            observe_only=record.config.observe_only or not record.config.enable_auto_click,
        )
        action = {
            "decision": decision.model_dump(),
            "result": {"executed": False, "reason": "evaluation_only", "status": "evaluated"},
        }
        action = self._build_action_audit(
            action,
            selected,
            before_image=latest.path,
            action_index=executed_count + 1,
            run_id=run_id,
            target_language=record.config.target_language,
        )
        self._write_action_audit(run_id, action)
        return [action]

    def execute_action(self, run_id: str) -> list[dict[str, object]]:
        prepared = self._prepare_controlled_action(run_id)
        if isinstance(prepared, dict):
            self._write_action_audit(run_id, prepared)
            return [prepared]

        record, latest, selected, executed_count = prepared
        action = self.actions.observe_or_click(
            selected,
            observe_only=record.config.observe_only or not record.config.enable_auto_click,
        )
        action = self._build_action_audit(
            action,
            selected,
            before_image=latest.path,
            action_index=executed_count + 1,
            run_id=run_id,
            target_language=record.config.target_language,
        )
        self._write_action_audit(run_id, action)
        return [action]

    def record_action_audit(self, run_id: str, action: dict[str, object]) -> dict[str, object]:
        self._write_action_audit(run_id, action)
        return action

    def _prepare_controlled_action(self, run_id: str):
        record = self.get_run(run_id)
        images = self.images(run_id)
        latest = images[-1] if images else None
        action_image = _latest_accepted_image(images)
        if action_image is None and latest is not None and latest.bucket in {"rejected", "manual_review", "deleted"}:
            self._append_observation_audit(run_id, [], latest.meta.get("ocr"))
            return self._stopped_action(f"image_bucket_{latest.bucket}", latest.path)
        action_image = action_image or latest

        candidates = self._candidates_for_image(run_id, record, action_image) if action_image is not None else []
        from ai_screenshot_platform.v3.schemas import FusedCandidate

        self._append_observation_audit(run_id, candidates, action_image.meta.get("ocr") if action_image else None)
        if not candidates or action_image is None:
            return self._stopped_action("no_candidates", action_image.path if action_image else None)
        executed_count = sum(1 for action in self.store.list_meta_jsonl(run_id, "actions.jsonl") if _result_executed(action))
        if executed_count >= record.config.max_actions:
            return self._stopped_action("max_actions_reached", action_image.path)

        selected = self._select_controlled_candidate(
            [FusedCandidate.model_validate(candidate) for candidate in candidates],
            clicked_labels=_clicked_labels(self.store.list_meta_jsonl(run_id, "actions.jsonl")),
            app_type=record.config.app_type,
        )
        if selected is None:
            region_block = _first_region_blocked_candidate([FusedCandidate.model_validate(candidate) for candidate in candidates])
            if region_block is not None:
                reason = region_block.blocked_reason or region_block.block_reason or "candidate_region_blocked"
                return self._stopped_action(
                    reason,
                    action_image.path,
                    candidate_region_type=region_block.candidate_region_type,
                    blocked_reason=reason,
                )
            return self._stopped_action("no_safe_ocr_candidate", action_image.path)
        return record, action_image, selected, executed_count

    def model_classify_scene(self, request: ModelRequest):
        return self.model_registry.classify_scene(request)

    def model_rank_click_candidates(self, request: ModelRequest):
        return self.model_registry.rank_click_candidates(request)

    def model_propose_visual_candidates(self, request: ModelRequest):
        return self.model_registry.propose_visual_candidates(request)

    def _append_observation_audit(self, run_id: str, candidates: list[dict[str, object]], ocr: object | None) -> None:
        self.store.append_meta_jsonl(run_id, "candidates.jsonl", {"candidates": [_candidate_audit_payload(candidate) for candidate in candidates]})
        if ocr is not None:
            self.store.append_meta_jsonl(run_id, "ocr.jsonl", ocr)

    def _select_controlled_candidate(
        self,
        candidates: list[FusedCandidate],
        clicked_labels: set[str],
        app_type: str = "auto",
    ) -> FusedCandidate | None:
        safe = [
            candidate
            for candidate in candidates
            if not candidate.blocked
            and not candidate.risk_flags
            and candidate.risk_penalty <= 0
            and (app_type != "pc_app" or candidate.candidate_region_type == "ui_chrome")
            and _candidate_inside_action_area(candidate, app_type)
        ]
        unclicked_safe = [candidate for candidate in safe if candidate.label.strip().casefold() not in clicked_labels]
        priority_labels = _SAFE_CLICK_LABELS if app_type == "pc_app" else _GENERIC_SAFE_CLICK_LABELS
        for pool in (unclicked_safe, safe):
            for label in priority_labels:
                for candidate in pool:
                    if candidate.source == "ocr_box" and candidate.label.strip().casefold() == label:
                        return candidate
            for candidate in pool:
                if candidate.source == "ocr_box":
                    return candidate
        return None

    def _build_action_audit(
        self,
        action: dict[str, object],
        candidate: FusedCandidate,
        before_image: str,
        action_index: int,
        run_id: str,
        target_language: str = "en",
    ) -> dict[str, object]:
        result = dict(action.get("result", {}))
        after_image = self._capture_after_image(run_id, action_index, before_image) if result.get("executed") else before_image
        if result.get("executed"):
            effect = self._evaluate_click_effect(run_id, before_image, after_image, target_language)
            result["status"] = effect["status"]
            if (
                result["status"] == "ui_changed"
                and self.get_run(run_id).config.app_type == "pc_app"
                and _is_menu_candidate_label(candidate.label)
            ):
                result["status"] = "menu_opened"
            if effect.get("rollback_reason"):
                result["rollback_reason"] = effect["rollback_reason"]
        action["result"] = result
        action["label"] = candidate.label
        action["source_candidate_id"] = _candidate_id(candidate)
        action["safety_result"] = action.get("decision", {})
        action["candidate_region_type"] = candidate.candidate_region_type
        action["blocked_reason"] = candidate.blocked_reason or candidate.block_reason or result.get("reason")
        action["before_image"] = before_image
        action["after_image"] = after_image
        action["click_backend"] = result.get("click_backend")
        return action

    def _evaluate_click_effect(self, run_id: str, before_image: str, after_image: str, target_language: str) -> dict[str, object]:
        before_sha = _file_sha256(before_image)
        after_sha = _file_sha256(after_image)
        effect: dict[str, object] = {
            "before_image": before_image,
            "after_image": after_image,
            "before_sha256": before_sha,
            "after_sha256": after_sha,
            "status": "no_effect" if before_sha == after_sha else "ui_changed",
        }
        if before_sha != after_sha:
            rollback_reason = self._rollback_reason_for_after_image(after_image, target_language)
            if rollback_reason:
                effect["status"] = "rollback_requested"
                effect["rollback_reason"] = rollback_reason
                self.store.append_meta_jsonl(run_id, "rollback.jsonl", rollback_plan(rollback_reason))
        self.store.append_meta_jsonl(run_id, "effect.jsonl", effect)
        return effect

    def _rollback_reason_for_after_image(self, after_image: str, target_language: str) -> str | None:
        try:
            ocr_result = self._recognize_for_target(after_image, target_language)
        except Exception as exc:
            return f"after_ocr_error:{exc}"
        if ocr_result.status != "ok":
            return f"after_ocr_status:{ocr_result.status}"
        for box in ocr_result.text_boxes:
            risks = risk_terms_in_text(box.text)
            if risks:
                return f"after_ocr_risk_terms:{','.join(risks)}"
            language = filter_language(box.text, target_language)
            if language.reason == "too_few_chars":
                continue
            if not language.accepted and not _is_low_confidence_short_noise(box.text, box.confidence):
                return f"after_ocr_language:{language.reason}"
        return None

    def _capture_after_image(self, run_id: str, action_index: int, before_image: str) -> str:
        if os.environ.get("APP_SHOT_CAPTURE_AFTER_CLICK", "").strip() != "1":
            return before_image
        try:
            from PIL import ImageGrab

            path = self.store.write_artifact(run_id, f"meta/after_{action_index}.png", "")
            path.unlink(missing_ok=True)
            ImageGrab.grab().save(path)
            return str(path)
        except Exception:
            return before_image

    def _stopped_action(
        self,
        reason: str,
        image_path: str | None,
        candidate_region_type: str | None = None,
        blocked_reason: str | None = None,
    ) -> dict[str, object]:
        return {
            "decision": {"allowed": False, "reason": reason},
            "result": {"executed": False, "reason": reason, "status": "stopped"},
            "source_candidate_id": None,
            "safety_result": {"allowed": False, "reason": reason},
            "candidate_region_type": candidate_region_type,
            "blocked_reason": blocked_reason or reason,
            "before_image": image_path,
            "after_image": image_path,
        }

    def _write_action_audit(self, run_id: str, action: dict[str, object]) -> None:
        self.store.write_artifact(run_id, "actions.json", [action])
        self.store.append_meta_jsonl(run_id, "actions.jsonl", action)
        self.store.append_meta_jsonl(run_id, "events.jsonl", {"event": "action_evaluated", "details": action})
        self.store.append_event(run_id, "action_evaluated", action)


_SAFE_CLICK_LABELS = [
    "file",
    "edit",
    "search",
    "view",
    "go to",
    "goto",
    "zoom",
    "favorites",
    "encoding",
    "language",
    "settings",
    "tools",
    "macro",
    "plugins",
    "window",
    "help",
    "about",
    "find",
    "aa",
    "page",
    "previous",
    "prev",
    "next page",
    "next",
    "page",
    "zoom",
    "fit page",
    "fit width",
    "single page",
    "continuous",
    "bookmarks",
    "aa",
    "文件",
    "编辑",
    "搜索",
    "视图",
    "编码",
    "语言",
    "设置",
    "工具",
    "宏",
    "插件",
    "窗口",
    "帮助",
    "start",
    "next",
    "confirm",
    "settings",
    "back",
    "cancel",
    "open project",
    "view report",
    "help center",
]


_GENERIC_SAFE_CLICK_LABELS = [
    "start",
    "next",
    "continue",
    "confirm",
    "ok",
    "back",
    "cancel",
    "open project",
    "view report",
    "help center",
]


def _candidate_id(candidate: FusedCandidate) -> str:
    bbox = ":".join(str(item) for item in candidate.bbox)
    return f"{candidate.source}:{candidate.label}:{bbox}"


def _candidate_audit_payload(candidate: dict[str, object]) -> dict[str, object]:
    payload = dict(candidate)
    payload.setdefault("candidate_source", payload.get("source"))
    payload.setdefault("text", payload.get("label"))
    payload.setdefault("score", payload.get("final_score", payload.get("confidence")))
    payload.setdefault("blocked_reason", payload.get("blocked_reason") or payload.get("block_reason"))
    return payload


def _clicked_labels(actions: list[dict[str, object]]) -> set[str]:
    return {
        str(action.get("label", "")).strip().casefold()
        for action in actions
        if _result_executed(action) and action.get("label")
    }


def _latest_accepted_image(images: list[V3ImageRecord]) -> V3ImageRecord | None:
    for image in reversed(images):
        if image.bucket == "accepted":
            return image
    return None


def _first_region_blocked_candidate(candidates: list[FusedCandidate]) -> FusedCandidate | None:
    for region in ("content_area", "unsafe_chrome"):
        for candidate in candidates:
            if candidate.candidate_region_type == region and candidate.blocked:
                return candidate
    return None


def _result_executed(action: dict[str, object]) -> bool:
    result = action.get("result", {})
    return isinstance(result, dict) and result.get("executed") is True


def _is_low_confidence_short_noise(text: str, confidence: float) -> bool:
    compact = "".join(text.split())
    return confidence < 0.65 and 0 < len(compact) <= 2


def _pc_app_target_language_dominates(app_type: str, boxes, target_language: str) -> bool:
    if app_type != "pc_app":
        return False
    target_chars = 0
    other_chars = 0
    for box in boxes:
        for char in box.text:
            script = _script_for_char(char)
            if script is None:
                continue
            if _script_matches_target(script, target_language):
                target_chars += 1
            else:
                other_chars += 1
    return target_chars >= 20 and target_chars >= other_chars * 3


def _is_safe_pc_app_ui_label(app_type: str, text: str) -> bool:
    if app_type != "pc_app":
        return False
    normalized = text.strip().casefold()
    return normalized in _SAFE_PC_APP_UI_LABELS


def _split_safe_pc_app_menu_boxes(app_type: str, boxes) -> list:
    if app_type != "pc_app":
        return []
    from ai_screenshot_platform.v3.schemas import OcrTextBox

    split_boxes: list[OcrTextBox] = []
    seen: set[tuple[str, tuple[int, int, int, int]]] = set()
    for box in boxes:
        text = box.text.strip()
        if _is_safe_pc_app_ui_label(app_type, text):
            continue
        if len(text) < 4:
            continue
        x1, y1, x2, y2 = box.bbox
        if y2 > 120:
            continue
        width = max(1, x2 - x1)
        text_len = max(1, len(text))
        for label in _SAFE_PC_APP_UI_LABELS:
            if len(label) <= 1:
                continue
            index = text.casefold().find(label.casefold())
            if index < 0:
                continue
            left = x1 + int(width * index / text_len)
            right = x1 + int(width * (index + len(label)) / text_len)
            bbox = [left, y1, max(left + 8, right), y2]
            key = (label, tuple(bbox))
            if key in seen:
                continue
            seen.add(key)
            split_boxes.append(
                OcrTextBox(
                    text=label,
                    bbox=bbox,
                    confidence=box.confidence,
                    language_hint=box.language_hint,
                )
            )
    return split_boxes


def _is_menu_candidate_label(label: str) -> bool:
    normalized = label.strip().casefold()
    return normalized in {
        "file",
        "edit",
        "search",
        "view",
        "go to",
        "goto",
        "zoom",
        "favorites",
        "settings",
        "help",
        "about",
        "文件",
        "编辑",
        "搜索",
        "视图",
        "设置",
        "帮助",
    }


def _candidate_inside_action_area(candidate: FusedCandidate, app_type: str) -> bool:
    if app_type != "pc_app":
        return True
    return candidate.click_y >= 28


def _classify_candidate_region(candidate: FusedCandidate, app_type: str) -> FusedCandidate:
    candidate.candidate_source = candidate.source
    if app_type != "pc_app":
        candidate.candidate_region_type = "unknown"
        return candidate
    label = candidate.label.strip()
    normalized = label.casefold().strip(" :：\t\r\n")
    x1, y1, x2, y2 = candidate.bbox
    if _is_unsafe_pc_app_label(normalized) or y1 < 28:
        candidate.candidate_region_type = "unsafe_chrome"
        candidate.blocked = True
        candidate.block_reason = "unsafe_chrome"
        candidate.blocked_reason = "unsafe_chrome"
        candidate.risk_penalty = max(candidate.risk_penalty, 1.0)
        return candidate
    if _is_pc_app_ui_chrome_label(normalized) or y2 <= 95:
        candidate.candidate_region_type = "ui_chrome"
        return candidate
    if _looks_like_document_body_text(label, candidate.bbox):
        candidate.candidate_region_type = "content_area"
        candidate.blocked = True
        candidate.block_reason = "content_area_not_clickable"
        candidate.blocked_reason = "content_area_not_clickable"
        return candidate
    candidate.candidate_region_type = "content_area"
    candidate.blocked = True
    candidate.block_reason = "content_area_not_clickable"
    candidate.blocked_reason = "content_area_not_clickable"
    return candidate


def _is_pc_app_ui_chrome_label(normalized: str) -> bool:
    return normalized in _PC_APP_UI_CHROME_LABELS


def _is_unsafe_pc_app_label(normalized: str) -> bool:
    return normalized in _UNSAFE_PC_APP_LABELS or any(term in normalized for term in _UNSAFE_PC_APP_LABEL_TERMS)


def _looks_like_document_body_text(text: str, bbox: list[int]) -> bool:
    compact = " ".join(text.split())
    if len(compact) >= 24:
        return True
    x1, y1, x2, y2 = bbox
    return y1 >= 120 and (x2 - x1) >= 120


_PC_APP_UI_CHROME_LABELS = {
    "file",
    "edit",
    "view",
    "go to",
    "goto",
    "merge",
    "navigate",
    "tools",
    "compare",
    "differences",
    "difference",
    "next difference",
    "previous difference",
    "first difference",
    "last difference",
    "zoom",
    "favorites",
    "settings",
    "help",
    "search",
    "find",
    "page",
    "page:",
    "fit page",
    "fit width",
    "single page",
    "continuous",
    "bookmarks",
    "previous",
    "next",
    "prev",
    "zoom in",
    "zoom out",
    "aa",
    "ok",
    "cancel",
    "close",
    "about",
    "options",
    "preferences",
    "refresh",
    "reload",
    "?",
}


_UNSAFE_PC_APP_LABELS = {
    "print",
    "save",
    "save as",
    "save left",
    "save right",
    "save merged",
    "exit",
    "quit",
    "open",
    "open file",
    "delete",
    "plugins admin",
    "minimize",
    "maximize",
    "close window",
}


_UNSAFE_PC_APP_LABEL_TERMS = {
    "http://",
    "https://",
    "www.",
    ".com",
    "@",
    "save left",
    "save right",
    "save merged",
    "save as",
    "delete",
    "print",
    "external command",
}


_SAFE_PC_APP_UI_LABELS = {
    "file",
    "edit",
    "search",
    "view",
    "merge",
    "navigate",
    "compare",
    "differences",
    "difference",
    "next difference",
    "previous difference",
    "first difference",
    "last difference",
    "go to",
    "goto",
    "zoom",
    "favorites",
    "encoding",
    "language",
    "settings",
    "tools",
    "options",
    "refresh",
    "reload",
    "macro",
    "plugins",
    "window",
    "help",
    "about",
    "fit page",
    "fit width",
    "single page",
    "continuous",
    "bookmarks",
    "aa",
    "page",
    "previous",
    "prev",
    "next page",
    "?",
    "preferences",
    "find",
    "replace",
    "word wrap",
    "zoom",
    "new",
    "open",
    "cancel",
    "back",
    "ok",
    "文件",
    "编辑",
    "搜索",
    "视图",
    "编码",
    "语言",
    "设置",
    "工具",
    "宏",
    "插件",
    "窗口",
    "帮助",
    "首选项",
    "查找",
    "替换",
    "自动换行",
    "缩放",
    "新建",
    "打开",
    "取消",
    "返回",
    "确定",
}


def _script_for_char(char: str) -> str | None:
    code = ord(char)
    if "a" <= char.lower() <= "z":
        return "latin"
    if "\u4e00" <= char <= "\u9fff":
        return "han"
    if 0x3040 <= code <= 0x30FF:
        return "japanese"
    if 0xAC00 <= code <= 0xD7AF:
        return "korean"
    return None


def _script_matches_target(script: str, target_language: str) -> bool:
    if target_language.startswith("en"):
        return script == "latin"
    if target_language.startswith("zh"):
        return script == "han"
    if target_language.startswith("ja"):
        return script in {"han", "japanese"}
    if target_language.startswith("ko"):
        return script == "korean"
    return True


def _accepted_text_class(app_type: str, ui_state_hint: str) -> str:
    if app_type in {"pc_game", "game"}:
        if ui_state_hint in {"main_view", "unknown"}:
            return "accepted_text_hud"
        return "accepted_text_ui"
    return "accepted_text_ui"


def _uses_no_text_policy(config: V3TaskConfig) -> bool:
    return config.app_type in {"pc_game", "game"} or config.text_policy in {"text_priority_with_fill", "visual_gameplay"}


def _file_sha256(path: str) -> str | None:
    image_path = Path(path)
    if not image_path.is_file():
        return None
    digest = hashlib.sha256()
    with image_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_int(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        kernel32.CloseHandle(handle)
        return True
    except Exception:
        return False


def _latest_image(folder: Path) -> Path | None:
    images = list_new_images(folder)
    if not images:
        return None
    return max(images, key=lambda item: item.stat().st_mtime)


def _build_duplicate_decision(
    *,
    content_hash: str | None,
    exact_duplicate: bool,
    compared_with: dict[str, str] | None,
    capture_reason: str,
    ui_state_hint: str,
    action_id: str | None,
    accepted_as_action_representative: bool,
    representative_group_key: str | None,
    representative_index: int | None,
    representative_limit: int,
    bucket: str,
    reject_reason: str | None,
    ocr_cache_hit: bool,
    existing_state_count: int,
) -> dict[str, object]:
    reason = _duplicate_decision_reason(
        exact_duplicate=exact_duplicate,
        capture_reason=capture_reason,
        bucket=bucket,
        reject_reason=reject_reason,
        accepted_as_action_representative=accepted_as_action_representative,
        ocr_cache_hit=ocr_cache_hit,
        existing_state_count=existing_state_count,
        compared_capture_reason=compared_with.get("capture_reason") if compared_with else None,
    )
    return {
        "content_hash": content_hash,
        "exact_duplicate": exact_duplicate,
        "near_duplicate": exact_duplicate,
        "duplicate_algorithm": "sha256_exact",
        "similarity_score": 1.0 if exact_duplicate else 0.0,
        "duplicate_threshold": 1.0,
        "compared_with_image_id": compared_with.get("image_id") if compared_with else None,
        "compared_with_image_path": compared_with.get("path") if compared_with else None,
        "capture_reason": capture_reason,
        "ui_state_hint": ui_state_hint,
        "action_id": action_id,
        "accepted_as_action_representative": accepted_as_action_representative,
        "representative_group_key": representative_group_key,
        "representative_index": representative_index,
        "representative_limit": representative_limit,
        "duplicate_decision_reason": reason,
    }


def _duplicate_decision_reason(
    *,
    exact_duplicate: bool,
    capture_reason: str,
    bucket: str,
    reject_reason: str | None,
    accepted_as_action_representative: bool,
    ocr_cache_hit: bool,
    existing_state_count: int,
    compared_capture_reason: str | None,
) -> str:
    if bucket == "accepted" and exact_duplicate and accepted_as_action_representative:
        if ocr_cache_hit and compared_capture_reason == capture_reason:
            return "ocr_cache_hit_same_hash"
        if capture_reason == "menu_state":
            return "menu_state_representative_accepted"
        if capture_reason == "dialog_state":
            return "dialog_state_representative_accepted"
        return "after_action_representative_accepted"
    if bucket == "accepted" and not exact_duplicate:
        if existing_state_count == 0:
            return "first_frame_for_ui_state"
        return "visual_difference_accepted"
    if bucket == "rejected" and exact_duplicate:
        if reject_reason == "near_duplicate" and capture_reason == "periodic":
            return "periodic_static_frame_rejected"
        if reject_reason == "near_duplicate":
            return "near_duplicate_rejected"
        return "exact_duplicate_rejected"
    if bucket == "rejected" and reject_reason:
        return str(reject_reason)
    if exact_duplicate:
        return "near_duplicate_rejected"
    return "visual_difference_accepted"
