from ai_screenshot_platform.v3.model.mock_ui_provider import MockUiModelProvider
from ai_screenshot_platform.v3.schemas import ModelRequest, OcrTextBox


def test_mock_ui_provider_ranks_ocr_boxes():
    provider = MockUiModelProvider()
    result = provider.rank_click_candidates(
        ModelRequest(
            screenshot_path="start.png",
            task_context={"app_type": "software"},
            ocr_boxes=[OcrTextBox(text="Start", bbox=[0, 0, 100, 40], confidence=0.9)],
        )
    )
    assert result.status == "ok"
    assert any(candidate.source == "ocr_box_and_mock_model" for candidate in result.candidates)
