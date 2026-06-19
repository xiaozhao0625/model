from ai_screenshot_platform.v3.action.candidate_fusion import fuse_candidates
from ai_screenshot_platform.v3.schemas import ModelClickCandidate


def test_candidate_fusion_blocks_risky_labels():
    safe = ModelClickCandidate(label="Start", source="ocr_box", bbox=[0, 0, 10, 10], click_x=5, click_y=5, confidence=0.8, reason="test")
    risky = ModelClickCandidate(label="Buy now", source="mock_ui_model", bbox=[0, 0, 10, 10], click_x=5, click_y=5, confidence=0.9, reason="test")
    fused = fuse_candidates([safe], [risky])
    assert any(item.blocked for item in fused if item.label == "Buy now")
    assert fused[0].label == "Start"
