from __future__ import annotations

from ai_screenshot_platform.v3.action.safety_gate import risk_terms_in_text
from ai_screenshot_platform.v3.schemas import FusedCandidate, ModelClickCandidate


def fuse_candidates(
    ocr: list[ModelClickCandidate],
    model: list[ModelClickCandidate],
    history_scores: dict[str, float] | None = None,
) -> list[FusedCandidate]:
    history_scores = history_scores or {}
    merged: list[FusedCandidate] = []
    for candidate in [*ocr, *model]:
        ocr_score = candidate.confidence if "ocr" in candidate.source else 0.0
        model_score = candidate.confidence if _is_ui_model_source(candidate.source) else 0.0
        layout_score = 0.5
        history_score = history_scores.get(candidate.label, 0.0)
        risks = risk_terms_in_text(candidate.label)
        risk_penalty = 1.0 if risks or candidate.risk_flags else 0.0
        score = 0.35 * ocr_score + 0.45 * model_score + 0.10 * layout_score + 0.10 * history_score - risk_penalty
        fused = FusedCandidate(
            **candidate.model_dump(),
            final_score=round(score, 4),
            ocr_button_score=ocr_score,
            ui_model_score=model_score,
            layout_score=layout_score,
            history_score=history_score,
            risk_penalty=risk_penalty,
            blocked=risk_penalty > 0,
            block_reason="risk_terms" if risk_penalty > 0 else None,
        )
        merged.append(fused)
    return sorted(merged, key=lambda item: item.final_score, reverse=True)


def _is_ui_model_source(source: str) -> bool:
    return "model" in source or source in {"showui", "omniparser"}
