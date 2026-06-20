from __future__ import annotations

import hashlib
import os
from pathlib import Path

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
    V3Health,
    V3ImageRecord,
    V3RunRecord,
    V3Summary,
    V3TaskConfig,
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

    def health(self) -> V3Health:
        return build_v3_health(self.model_registry)

    def action_health(self) -> dict[str, object]:
        return load_input_gateway_readiness().model_dump()

    def defaults(self) -> V3TaskConfig:
        return V3TaskConfig()

    def create_run(self, config: V3TaskConfig) -> V3RunRecord:
        return self.store.create_run(config)

    def list_runs(self) -> list[V3RunRecord]:
        return self.store.list_runs()

    def get_run(self, run_id: str) -> V3RunRecord:
        return self.store.get_run(run_id)

    def start_run(self, run_id: str) -> V3RunRecord:
        record = self.store.update_status(run_id, "running")
        self.store.append_event(run_id, "run_started", {"observe_only": record.config.observe_only})
        return record

    def pause_run(self, run_id: str) -> V3RunRecord:
        return self.store.update_status(run_id, "paused")

    def stop_run(self, run_id: str) -> V3RunRecord:
        return self.store.update_status(run_id, "stopped")

    def summary(self, run_id: str) -> V3Summary:
        health = self.health()
        ocr_ready = any(item.status == "ready" for item in health.ocr)
        model_ready = any(item.provider == "showui" and item.status == "ready" and item.enabled for item in health.models)
        return self.store.summary(
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
        bucket = "pending"
        reject_reason = None
        if not quality["accepted"]:
            bucket = "rejected"
            reject_reason = str(quality["reason"])
        duplicate_preserved = False
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
        if bucket == "pending" and record.config.enable_ocr:
            if duplicate_preserved and digest and digest in self._ocr_by_sha:
                ocr_result = self._ocr_by_sha[digest]
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
                elif record.config.must_have_text and not ocr_result.text_boxes:
                    bucket = "rejected"
                    reject_reason = "no_text"
                elif record.config.must_have_text:
                    bucket = "rejected"
                    reject_reason = "wrong_language"
        if bucket == "accepted" and duplicate_preserved:
            self._mark_action_duplicate_preserved(run_id, capture_reason, action_id, ui_state_hint)
        image = V3ImageRecord(
            image_id=path.stem,
            path=str(path),
            bucket=bucket,  # type: ignore[arg-type]
            sha256=digest,
            content_hash=digest,
            valid=bool(quality["accepted"]),
            near_duplicate=bool(quality["accepted"] and not unique),
            reject_reason=reject_reason,
            meta=meta,
        )
        return self.store.add_image(run_id, image)

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
            and candidate.label.strip().casefold() not in clicked_labels
            and _candidate_inside_action_area(candidate, app_type)
        ]
        priority_labels = _SAFE_CLICK_LABELS if app_type == "pc_app" else _GENERIC_SAFE_CLICK_LABELS
        for label in priority_labels:
            for candidate in safe:
                if candidate.source == "ocr_box" and candidate.label.strip().casefold() == label:
                    return candidate
        for candidate in safe:
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
    if _is_sumatra_ui_chrome_label(normalized) or y2 <= 95:
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


def _is_sumatra_ui_chrome_label(normalized: str) -> bool:
    return normalized in _SUMATRA_UI_CHROME_LABELS


def _is_unsafe_pc_app_label(normalized: str) -> bool:
    return normalized in _UNSAFE_PC_APP_LABELS or any(term in normalized for term in _UNSAFE_PC_APP_LABEL_TERMS)


def _looks_like_document_body_text(text: str, bbox: list[int]) -> bool:
    compact = " ".join(text.split())
    if len(compact) >= 24:
        return True
    x1, y1, x2, y2 = bbox
    return y1 >= 120 and (x2 - x1) >= 120


_SUMATRA_UI_CHROME_LABELS = {
    "file",
    "view",
    "go to",
    "goto",
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
    "?",
}


_UNSAFE_PC_APP_LABELS = {
    "print",
    "save as",
    "exit",
    "quit",
    "open",
    "open file",
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
}


_SAFE_PC_APP_UI_LABELS = {
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


def _file_sha256(path: str) -> str | None:
    image_path = Path(path)
    if not image_path.is_file():
        return None
    digest = hashlib.sha256()
    with image_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
