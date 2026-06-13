from __future__ import annotations

from ai_screenshot_platform.common.action_gateway.contracts import ActionGatewayRequest
from ai_screenshot_platform.common.action_gateway.execution_guard import ActionGateway
from ai_screenshot_platform.common.ocr.contracts import OcrRiskHit


def test_action_gateway_blocks_ocr_risks_before_execution():
    decision = ActionGateway().evaluate(
        ActionGatewayRequest(
            action_type="click",
            instruction="点击继续",
            ocr_risk_hits=[OcrRiskHit(risk_type="captcha", matched_text="验证码", action="block_action")],
        )
    )

    assert decision.allowed is False
    assert decision.blocked_by == "ocr_risk"
