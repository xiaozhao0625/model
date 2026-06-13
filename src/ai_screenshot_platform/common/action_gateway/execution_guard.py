from __future__ import annotations

from ai_screenshot_platform.common.action_gateway.contracts import (
    ActionGatewayDecision,
    ActionGatewayRequest,
)
from ai_screenshot_platform.common.action_gateway.ocr_action_guard import OcrActionGuard
from ai_screenshot_platform.common.action_gateway.risk_guard import TextRiskGuard


class ActionGateway:
    def evaluate(self, request: ActionGatewayRequest) -> ActionGatewayDecision:
        ocr_risks = OcrActionGuard().detect(request.ocr_risk_hits)
        if ocr_risks:
            return ActionGatewayDecision(False, "request_manual", "ocr_risk", ocr_risks, "ocr_risk_blocked")
        risk_flags = list(request.risk_flags)
        risk_flags.extend(TextRiskGuard().detect(request.instruction))
        if risk_flags:
            return ActionGatewayDecision(False, "request_manual", "text_or_flag_risk", risk_flags, "risk_blocked")
        return ActionGatewayDecision(True, request.action_type, reason="safe")
