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


def test_safety_gate_blocks_multilingual_risk_terms():
    for label in ["Login", "Payment", "Buy Now", "Delete Account", "Password", "Captcha Verify", "ログイン", "支払い", "購入", "アカウント削除", "パスワード", "認証コード", "로그인", "결제", "구매", "계정 삭제", "비밀번호", "인증 코드"]:
        candidate = FusedCandidate(
            label=label,
            source="ocr_box",
            bbox=[0, 0, 10, 10],
            click_x=5,
            click_y=5,
            confidence=0.8,
            reason="test",
            final_score=0.5,
        )
        decision = SafetyGate().evaluate("click", candidate=candidate, observe_only=False)
        assert not decision.allowed, label
        assert "risk_terms" in decision.reason


def test_safety_gate_does_not_block_safe_report_label():
    candidate = FusedCandidate(
        label="View Report",
        source="ocr_box",
        bbox=[0, 0, 10, 10],
        click_x=5,
        click_y=5,
        confidence=0.8,
        reason="test",
        final_score=0.5,
    )
    decision = SafetyGate().evaluate("click", candidate=candidate, observe_only=False)
    assert decision.allowed
