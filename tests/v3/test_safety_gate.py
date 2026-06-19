from ai_screenshot_platform.v3.action.safety_gate import SafetyGate
from ai_screenshot_platform.v3.schemas import FusedCandidate


def test_safety_gate_blocks_observe_only_clicks():
    candidate = FusedCandidate(
        label="Start",
        source="ocr_box",
        bbox=[0, 0, 10, 10],
        click_x=5,
        click_y=5,
        confidence=0.8,
        reason="test",
        final_score=0.5,
    )
    decision = SafetyGate().evaluate("click", candidate=candidate, observe_only=True)
    assert not decision.allowed
    assert decision.reason == "observe_only_blocks_click"


def test_safety_gate_blocks_risk_terms():
    candidate = FusedCandidate(
        label="password",
        source="mock_ui_model",
        bbox=[0, 0, 10, 10],
        click_x=5,
        click_y=5,
        confidence=0.8,
        reason="test",
        final_score=0.5,
    )
    decision = SafetyGate().evaluate("click", candidate=candidate, observe_only=False)
    assert not decision.allowed
    assert "risk_terms" in decision.reason
