from __future__ import annotations

from ai_screenshot_platform.v3.model.base import UiModelProvider
from ai_screenshot_platform.v3.schemas import (
    ModelClickCandidate,
    ModelRequest,
    ModelResult,
    ProviderHealth,
    SceneClassification,
)


class MockUiModelProvider(UiModelProvider):
    provider_name = "mock_ui_model"

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=True, reason="mock provider")

    def classify_scene(self, request: ModelRequest) -> ModelResult:
        scene = "game_in_match" if request.task_context.get("app_type") == "game" else "software_ui"
        return ModelResult(
            provider=self.provider_name,
            status="ok",
            scene=SceneClassification(scene_class=scene, confidence=0.6, reason="mock_context_rule"),
        )

    def propose_visual_candidates(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            provider=self.provider_name,
            status="ok",
            candidates=[
                ModelClickCandidate(
                    label="primary_visual_candidate",
                    source="mock_ui_model",
                    bbox=[32, 32, 180, 90],
                    click_x=106,
                    click_y=61,
                    confidence=0.72,
                    reason="mock primary button-like region",
                )
            ],
        )

    def rank_click_candidates(self, request: ModelRequest) -> ModelResult:
        result = self.propose_visual_candidates(request)
        result.candidates.extend(
            ModelClickCandidate(
                label=box.text,
                source="ocr_box_and_mock_model",
                bbox=box.bbox,
                click_x=(box.bbox[0] + box.bbox[2]) // 2,
                click_y=(box.bbox[1] + box.bbox[3]) // 2,
                confidence=min(0.95, max(0.1, box.confidence)),
                reason="OCR text box re-ranked by mock UI model",
            )
            for box in request.ocr_boxes
        )
        return result
