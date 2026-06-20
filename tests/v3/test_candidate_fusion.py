from ai_screenshot_platform.v3.action.candidate_fusion import fuse_candidates
from ai_screenshot_platform.v3.schemas import ModelClickCandidate


def test_candidate_fusion_blocks_risky_labels():
    safe = ModelClickCandidate(label="Start", source="ocr_box", bbox=[0, 0, 10, 10], click_x=5, click_y=5, confidence=0.8, reason="test")
    risky = ModelClickCandidate(label="Buy now", source="mock_ui_model", bbox=[0, 0, 10, 10], click_x=5, click_y=5, confidence=0.9, reason="test")
    fused = fuse_candidates([safe], [risky])
    assert any(item.blocked for item in fused if item.label == "Buy now")
    assert fused[0].label == "Start"


def test_candidate_fusion_scores_showui_as_ui_model():
    candidate = ModelClickCandidate(label="Start", source="showui", bbox=[0, 0, 10, 10], click_x=5, click_y=5, confidence=0.9, reason="test")
    fused = fuse_candidates([], [candidate])
    assert fused[0].ui_model_score == 0.9


def test_candidate_fusion_blocks_file_operation_labels_without_rejecting_safe_menu_labels():
    safe = ModelClickCandidate(label="File", source="ocr_box", bbox=[0, 0, 10, 10], click_x=5, click_y=5, confidence=0.8, reason="test")
    print_item = ModelClickCandidate(label="Print", source="ocr_box", bbox=[0, 12, 10, 22], click_x=5, click_y=17, confidence=0.8, reason="test")
    save_as = ModelClickCandidate(label="Save As", source="ocr_box", bbox=[0, 24, 10, 34], click_x=5, click_y=29, confidence=0.8, reason="test")
    exit_item = ModelClickCandidate(label="Exit", source="ocr_box", bbox=[0, 36, 10, 46], click_x=5, click_y=41, confidence=0.8, reason="test")

    fused = fuse_candidates([safe, print_item, save_as, exit_item], [])

    assert next(item for item in fused if item.label == "File").blocked is False
    assert next(item for item in fused if item.label == "Print").blocked is True
    assert next(item for item in fused if item.label == "Save As").blocked is True
    assert next(item for item in fused if item.label == "Exit").blocked is True
