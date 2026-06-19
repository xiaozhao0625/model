from __future__ import annotations

import os
from pathlib import Path

from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.action.action_loop import ActionLoop
from ai_screenshot_platform.v3.action.candidate_fusion import fuse_candidates
from ai_screenshot_platform.v3.action.candidate_generator import ocr_candidates
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

    def health(self) -> V3Health:
        return build_v3_health(self.model_registry)

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
        model_ready = health.complete_auto_mode_ready
        return self.store.summary(run_id, ocr_ready=ocr_ready, model_ready=model_ready, safety_gate_ready=True)

    def images(self, run_id: str) -> list[V3ImageRecord]:
        return self.store.list_images(run_id)

    def events(self, run_id: str):
        return self.store.list_events(run_id)

    def ingest_image(self, run_id: str, image_path: str) -> V3ImageRecord:
        record = self.get_run(run_id)
        path = Path(image_path)
        quality = basic_image_quality(path)
        unique = False
        digest: str | None = None
        if quality["accepted"]:
            unique, digest = self.duplicates.check(path)
        bucket = "pending"
        reject_reason = None
        if not quality["accepted"]:
            bucket = "rejected"
            reject_reason = str(quality["reason"])
        elif not unique:
            bucket = "rejected"
            reject_reason = "near_duplicate"
        meta: dict[str, object] = {"capture_source": record.config.capture_source, "quality": quality}
        if bucket == "pending" and record.config.enable_ocr:
            ocr_result = self._recognize_for_target(str(path), record.config.target_language)
            meta["ocr"] = ocr_result.model_dump()
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
                if accepted_boxes:
                    if rejected_language_results:
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
        image = V3ImageRecord(
            image_id=path.stem,
            path=str(path),
            bucket=bucket,  # type: ignore[arg-type]
            sha256=digest,
            reject_reason=reject_reason,
            meta=meta,
        )
        return self.store.add_image(run_id, image)

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
        latest = images[-1]
        if isinstance(latest.meta.get("ocr"), dict):
            from ai_screenshot_platform.v3.schemas import OcrResult

            ocr_result = OcrResult.model_validate(latest.meta["ocr"])
        else:
            ocr_result = self._active_ocr_provider().recognize(latest.path)
        valid_boxes = [
            box
            for box in ocr_result.text_boxes
            if filter_language(box.text, record.config.target_language).accepted or record.config.app_type == "game"
        ]
        ocr_clicks = ocr_candidates(valid_boxes)
        model_request = ModelRequest(
            screenshot_path=latest.path,
            task_context=record.config.model_dump(),
            ocr_boxes=valid_boxes,
        )
        model_result = self.model_registry.rank_click_candidates(model_request)
        fused = fuse_candidates(ocr_clicks, model_result.candidates)
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
        )
        self._write_action_audit(run_id, action)
        return [action]

    def _prepare_controlled_action(self, run_id: str):
        record = self.get_run(run_id)
        images = self.images(run_id)
        latest = images[-1] if images else None
        if latest is not None and latest.bucket in {"rejected", "manual_review", "deleted"}:
            self._append_observation_audit(run_id, [], latest.meta.get("ocr"))
            return self._stopped_action(f"image_bucket_{latest.bucket}", latest.path)

        candidates = self.candidates(run_id)
        from ai_screenshot_platform.v3.schemas import FusedCandidate

        self._append_observation_audit(run_id, candidates, latest.meta.get("ocr") if latest else None)
        if not candidates or latest is None:
            return self._stopped_action("no_candidates", latest.path if latest else None)
        executed_count = sum(1 for action in self.store.list_meta_jsonl(run_id, "actions.jsonl") if _result_executed(action))
        if executed_count >= record.config.max_actions:
            return self._stopped_action("max_actions_reached", latest.path)

        selected = self._select_controlled_candidate(
            [FusedCandidate.model_validate(candidate) for candidate in candidates],
            clicked_labels=_clicked_labels(self.store.list_meta_jsonl(run_id, "actions.jsonl")),
        )
        if selected is None:
            return self._stopped_action("no_safe_ocr_candidate", latest.path)
        return record, latest, selected, executed_count

    def model_classify_scene(self, request: ModelRequest):
        return self.model_registry.classify_scene(request)

    def model_rank_click_candidates(self, request: ModelRequest):
        return self.model_registry.rank_click_candidates(request)

    def model_propose_visual_candidates(self, request: ModelRequest):
        return self.model_registry.propose_visual_candidates(request)

    def _append_observation_audit(self, run_id: str, candidates: list[dict[str, object]], ocr: object | None) -> None:
        self.store.append_meta_jsonl(run_id, "candidates.jsonl", {"candidates": candidates})
        if ocr is not None:
            self.store.append_meta_jsonl(run_id, "ocr.jsonl", ocr)

    def _select_controlled_candidate(
        self,
        candidates: list[FusedCandidate],
        clicked_labels: set[str],
    ) -> FusedCandidate | None:
        safe = [
            candidate
            for candidate in candidates
            if not candidate.blocked
            and not candidate.risk_flags
            and candidate.risk_penalty <= 0
            and candidate.label.strip().casefold() not in clicked_labels
        ]
        for label in _SAFE_CLICK_LABELS:
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
    ) -> dict[str, object]:
        result = dict(action.get("result", {}))
        after_image = self._capture_after_image(run_id, action_index, before_image) if result.get("executed") else before_image
        if result.get("executed"):
            result["status"] = "no_effect"
        action["result"] = result
        action["label"] = candidate.label
        action["source_candidate_id"] = _candidate_id(candidate)
        action["safety_result"] = action.get("decision", {})
        action["before_image"] = before_image
        action["after_image"] = after_image
        return action

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

    def _stopped_action(self, reason: str, image_path: str | None) -> dict[str, object]:
        return {
            "decision": {"allowed": False, "reason": reason},
            "result": {"executed": False, "reason": reason, "status": "stopped"},
            "source_candidate_id": None,
            "safety_result": {"allowed": False, "reason": reason},
            "before_image": image_path,
            "after_image": image_path,
        }

    def _write_action_audit(self, run_id: str, action: dict[str, object]) -> None:
        self.store.write_artifact(run_id, "actions.json", [action])
        self.store.append_meta_jsonl(run_id, "actions.jsonl", action)
        self.store.append_meta_jsonl(run_id, "events.jsonl", {"event": "action_evaluated", "details": action})
        self.store.append_event(run_id, "action_evaluated", action)


_SAFE_CLICK_LABELS = [
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


def _candidate_id(candidate: FusedCandidate) -> str:
    bbox = ":".join(str(item) for item in candidate.bbox)
    return f"{candidate.source}:{candidate.label}:{bbox}"


def _clicked_labels(actions: list[dict[str, object]]) -> set[str]:
    return {
        str(action.get("label", "")).strip().casefold()
        for action in actions
        if _result_executed(action) and action.get("label")
    }


def _result_executed(action: dict[str, object]) -> bool:
    result = action.get("result", {})
    return isinstance(result, dict) and result.get("executed") is True


def _is_low_confidence_short_noise(text: str, confidence: float) -> bool:
    compact = "".join(text.split())
    return confidence < 0.65 and 0 < len(compact) <= 2
