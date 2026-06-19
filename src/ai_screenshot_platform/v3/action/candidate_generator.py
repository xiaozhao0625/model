from __future__ import annotations

from ai_screenshot_platform.v3.capture.coordinate_mapper import map_bbox_to_click
from ai_screenshot_platform.v3.schemas import ModelClickCandidate, OcrTextBox


BUTTON_WORDS = {"ok", "start", "next", "continue", "confirm", "开始", "确定", "继续", "下一步"}


def ocr_candidates(boxes: list[OcrTextBox]) -> list[ModelClickCandidate]:
    candidates: list[ModelClickCandidate] = []
    for box in boxes:
        x, y = map_bbox_to_click(box.bbox)
        text = box.text.strip()
        is_button_like = text.lower() in BUTTON_WORDS
        candidates.append(
            ModelClickCandidate(
                label=text,
                source="ocr_box",
                bbox=box.bbox,
                click_x=x,
                click_y=y,
                confidence=min(0.95, box.confidence + (0.1 if is_button_like else 0.0)),
                reason="button_keyword" if is_button_like else "ocr_text_box",
            )
        )
    return candidates
