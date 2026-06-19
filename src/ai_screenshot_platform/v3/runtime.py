from __future__ import annotations

from pathlib import Path

from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.action.action_loop import ActionLoop
from ai_screenshot_platform.v3.action.candidate_fusion import fuse_candidates
from ai_screenshot_platform.v3.action.candidate_generator import ocr_candidates
from ai_screenshot_platform.v3.model.health import build_v3_health
from ai_screenshot_platform.v3.model.registry import UiModelRegistry
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
    ) -> None:
        self.store = store or V3RunStore()
        self.model_registry = model_registry or UiModelRegistry()
        self.mock_ocr = MockOcrProvider()
        self.paddle_ocr = PaddleOcrProvider()
        self.ocr_provider = ocr_provider
        self.duplicates = DuplicateFilter()
        self.actions = ActionLoop()

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
            ocr_result = self._active_ocr_provider().recognize(str(path))
            meta["ocr"] = ocr_result.model_dump()
            if ocr_result.status != "ok":
                bucket = "manual_review"
                reject_reason = ocr_result.error or ocr_result.status
            else:
                accepted_boxes = [
                    box
                    for box in ocr_result.text_boxes
                    if filter_language(box.text, record.config.target_language).accepted
                ]
                if accepted_boxes:
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
        record = self.get_run(run_id)
        candidates = self.candidates(run_id)
        if not candidates:
            return []
        from ai_screenshot_platform.v3.schemas import FusedCandidate

        top = FusedCandidate.model_validate(candidates[0])
        result = self.actions.observe_or_click(top, observe_only=record.config.observe_only or not record.config.enable_auto_click)
        self.store.write_artifact(run_id, "actions.json", [result])
        self.store.append_event(run_id, "action_evaluated", result)
        return [result]

    def model_classify_scene(self, request: ModelRequest):
        return self.model_registry.classify_scene(request)

    def model_rank_click_candidates(self, request: ModelRequest):
        return self.model_registry.rank_click_candidates(request)

    def model_propose_visual_candidates(self, request: ModelRequest):
        return self.model_registry.propose_visual_candidates(request)
