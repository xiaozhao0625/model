import json
from pathlib import Path

import pytest

from ai_screenshot_platform.common.model_gateway.contracts import (
    ActRequest,
    ActionProposal,
    ActionType,
    SceneClass,
)
from ai_screenshot_platform.common.model_gateway.gateway_service import (
    ModelGatewayService,
    ModelGatewayServiceError,
)
from ai_screenshot_platform.common.model_gateway.risk_lexicon import (
    RiskLexiconLoader,
)
from ai_screenshot_platform.common.model_gateway.risk_rules import RiskRuleDetector


class SafeProvider:
    provider_name = "safe"

    def scene_classify(self, request):
        raise NotImplementedError

    def ground(self, request):
        raise NotImplementedError

    def act(self, request: ActRequest) -> ActionProposal:
        return ActionProposal(
            action_type=ActionType.CLICK,
            confidence=0.9,
            reason="safe provider proposal",
            target={"x": 1, "y": 2},
            keys=[],
            risk_flags=[],
            provider_name=self.provider_name,
        )


def make_request(
    instruction: str = "click continue",
    context: dict | None = None,
    target_description: str | None = None,
) -> ActRequest:
    return ActRequest(
        app_id="demo_app",
        run_id="demo_run",
        screenshot_path="runs/demo/screen.webp",
        scene_class=SceneClass.MENU,
        instruction=instruction,
        target_description=target_description,
        context=context or {},
    )


def detector() -> RiskRuleDetector:
    return RiskRuleDetector(RiskLexiconLoader.load_default())


def test_english_captcha_risk_is_detected():
    assert "captcha" in detector().detect_act_request(
        make_request("solve captcha")
    )


def test_chinese_captcha_risk_is_detected():
    assert "captcha" in detector().detect_act_request(
        make_request("处理验证码")
    )


def test_english_payment_risk_is_detected():
    assert "payment" in detector().detect_act_request(
        make_request("go to checkout and pay")
    )


def test_chinese_payment_risk_is_detected():
    assert "payment" in detector().detect_act_request(
        make_request("打开收银台并支付")
    )


def test_chinese_recharge_risk_is_detected():
    assert "recharge" in detector().detect_act_request(
        make_request("进入充值页面")
    )


def test_chinese_send_chat_risk_is_detected():
    assert "send_chat" in detector().detect_act_request(
        make_request("发送聊天消息")
    )


def test_nested_context_anti_cheat_bypass_risk_is_detected():
    flags = detector().detect_act_request(
        make_request(
            context={
                "steps": [
                    {"mode": "绕过检测"},
                    {"note": "normal"},
                ]
            }
        )
    )

    assert "anti_cheat_bypass" in flags


def test_target_description_risk_is_detected():
    assert "purchase" in detector().detect_act_request(
        make_request(target_description="购买 button")
    )


def test_safe_instruction_is_not_falsely_blocked():
    assert detector().detect_act_request(make_request("click continue")) == []


def test_gateway_service_uses_risk_lexicon_to_block_act(tmp_path):
    service = ModelGatewayService(SafeProvider(), run_dir=tmp_path)

    proposal = service.act(make_request("请完成滑块验证"))

    assert proposal.action_type in {ActionType.REQUEST_MANUAL, ActionType.ABORT}
    assert "captcha" in proposal.risk_flags


def test_audit_log_is_written_to_run_dir_model_gateway_log(tmp_path):
    service = ModelGatewayService(SafeProvider(), run_dir=tmp_path)

    service.act(make_request())

    assert service.audit_log_path == tmp_path.resolve() / "model_gateway.log"
    assert service.audit_log_path.is_file()


def test_explicit_audit_log_path_inside_run_dir_is_allowed(tmp_path):
    audit_log_path = tmp_path / "audit" / "model_gateway.log"
    service = ModelGatewayService(
        SafeProvider(),
        run_dir=tmp_path,
        audit_log_path=audit_log_path,
    )

    service.act(make_request())

    assert audit_log_path.is_file()


def test_audit_log_path_escape_from_run_dir_is_rejected(tmp_path):
    with pytest.raises(ModelGatewayServiceError, match="run_dir"):
        ModelGatewayService(
            SafeProvider(),
            run_dir=tmp_path / "run",
            audit_log_path=tmp_path / "outside.log",
        )


def test_missing_audit_log_path_and_run_dir_fails_on_act():
    service = ModelGatewayService(SafeProvider())

    with pytest.raises(ModelGatewayServiceError, match="audit_log_path or run_dir"):
        service.act(make_request())


def test_default_risk_lexicon_config_has_required_risk_types():
    lexicon_path = Path("configs/safety/risk_lexicon.json")

    payload = json.loads(lexicon_path.read_text(encoding="utf-8"))

    assert set(payload) == {
        "captcha",
        "payment",
        "recharge",
        "purchase",
        "send_chat",
        "account_security",
        "anti_cheat_bypass",
    }
