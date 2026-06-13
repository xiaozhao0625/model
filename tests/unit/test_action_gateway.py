from __future__ import annotations

from ai_screenshot_platform.common.action_gateway.contracts import ActionGatewayRequest
from ai_screenshot_platform.common.action_gateway.execution_guard import ActionGateway


def test_action_gateway_allows_safe_wait_and_blocks_payment():
    gateway = ActionGateway()

    safe = gateway.evaluate(ActionGatewayRequest(action_type="wait", instruction="等待页面加载"))
    blocked = gateway.evaluate(ActionGatewayRequest(action_type="click", instruction="确认支付"))

    assert safe.allowed is True
    assert blocked.allowed is False
    assert blocked.final_action == "request_manual"
