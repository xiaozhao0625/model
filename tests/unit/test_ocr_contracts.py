from __future__ import annotations

from ai_screenshot_platform.common.ocr.contracts import OcrInput, OcrProviderStatus
from ai_screenshot_platform.common.ocr.disabled_adapter import DisabledOcrAdapter
from ai_screenshot_platform.common.ocr.easyocr_adapter import EasyOcrOptionalAdapter
from ai_screenshot_platform.common.ocr.mock_adapter import MockOcrAdapter
from ai_screenshot_platform.common.ocr.paddle_adapter import PaddleOcrOptionalAdapter
from ai_screenshot_platform.common.ocr.router import OcrRouter


def test_disabled_adapter_returns_skipped_unavailable():
    result = DisabledOcrAdapter().run_ocr(OcrInput(image_bytes=b"img"))

    assert result.available is False
    assert result.status == OcrProviderStatus.SKIPPED
    assert result.error_reason == "ocr_disabled"


def test_mock_adapter_returns_text_blocks_and_detects_risk():
    result = MockOcrAdapter(mock_text="验证码 支付 chat").run_ocr(OcrInput(image_bytes=b"img"))

    assert result.available is True
    assert result.text_blocks
    assert {hit.risk_type for hit in result.risk_hits} >= {"captcha", "payment", "chat_send"}


def test_router_defaults_to_disabled_and_can_use_mock():
    disabled = OcrRouter.from_policy({"default_provider": "disabled"}).run_ocr(OcrInput())
    mocked = OcrRouter.from_policy(
        {"default_provider": "mock", "mock_text": "账号安全"}
    ).run_ocr(OcrInput())

    assert disabled.status == OcrProviderStatus.SKIPPED
    assert mocked.risk_hits[0].risk_type == "account_security"


def test_optional_real_ocr_adapters_do_not_require_dependencies():
    paddle = PaddleOcrOptionalAdapter().run_ocr(OcrInput(image_bytes=b"img"))
    easy = EasyOcrOptionalAdapter().run_ocr(OcrInput(image_bytes=b"img"))

    assert paddle.available is False
    assert easy.available is False
    assert paddle.status == OcrProviderStatus.UNAVAILABLE
    assert easy.status == OcrProviderStatus.UNAVAILABLE
