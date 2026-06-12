import pytest

from ai_screenshot_platform.common.model_gateway.contracts import (
    ActRequest,
    ActionProposal,
    ActionType,
    GroundRequest,
    ModelTaskType,
    SceneClass,
    SceneClassifyRequest,
)
from ai_screenshot_platform.common.model_gateway.mock_provider import (
    MockModelGatewayProvider,
)
from ai_screenshot_platform.common.model_gateway.safety import ModelActionSafetyGate


def test_mock_provider_returns_scene_classify_result():
    provider = MockModelGatewayProvider()
    request = SceneClassifyRequest(
        app_id="demo_app",
        run_id="demo_run",
        screenshot_path="runs/demo/screen.webp",
        context={"mock_scene_class": SceneClass.MENU.value},
    )

    result = provider.scene_classify(request)

    assert result.scene_class == SceneClass.MENU
    assert result.provider_name == "mock"
    assert 0 <= result.confidence <= 1


def test_mock_provider_returns_ground_result():
    provider = MockModelGatewayProvider(mock_x=120, mock_y=240)
    request = GroundRequest(
        app_id="demo_app",
        run_id="demo_run",
        screenshot_path="runs/demo/screen.webp",
        target_description="start button",
        context={},
    )

    result = provider.ground(request)

    assert result.found is True
    assert result.x == 120
    assert result.y == 240
    assert result.provider_name == "mock"


def test_mock_provider_returns_act_result():
    provider = MockModelGatewayProvider()
    request = ActRequest(
        app_id="demo_app",
        run_id="demo_run",
        screenshot_path="runs/demo/screen.webp",
        scene_class=SceneClass.UNKNOWN,
        instruction="wait for next low-frequency decision",
        context={"mock_action_type": ActionType.REQUEST_MANUAL.value},
    )

    proposal = provider.act(request)

    assert proposal.action_type == ActionType.REQUEST_MANUAL
    assert proposal.provider_name == "mock"


def test_action_proposal_does_not_execute_real_actions():
    proposal = ActionProposal(
        action_type=ActionType.CLICK,
        confidence=0.9,
        reason="proposal only",
        target={"x": 10, "y": 20},
        keys=[],
        risk_flags=[],
        provider_name="mock",
    )

    assert not hasattr(proposal, "execute")
    assert proposal.action_type == ActionType.CLICK


def test_safe_action_passes_safety_gate():
    proposal = ActionProposal(
        action_type=ActionType.CLICK,
        confidence=0.9,
        reason="safe navigation click",
        target={"x": 10, "y": 20},
        keys=[],
        risk_flags=[],
        provider_name="mock",
    )

    checked = ModelActionSafetyGate().validate(proposal)

    assert checked == proposal


@pytest.mark.parametrize(
    "risk_flag",
    [
        "captcha",
        "payment",
        "purchase",
        "send_chat",
        "anti_cheat_bypass",
    ],
)
def test_forbidden_risk_flags_are_rejected(risk_flag):
    proposal = ActionProposal(
        action_type=ActionType.CLICK,
        confidence=0.8,
        reason="unsafe click",
        target={"x": 10, "y": 20},
        keys=[],
        risk_flags=[risk_flag],
        provider_name="mock",
    )

    checked = ModelActionSafetyGate().validate(proposal)

    assert checked.action_type in {ActionType.REQUEST_MANUAL, ActionType.ABORT}
    assert checked.action_type != ActionType.CLICK
    assert risk_flag in checked.risk_flags
    assert risk_flag in checked.reason


def test_contract_enums_include_required_values_only_for_actions():
    assert {task.value for task in ModelTaskType} == {
        "scene_classify",
        "ground",
        "act",
    }
    assert {action.value for action in ActionType} == {
        "click",
        "key_press",
        "wait",
        "no_op",
        "request_manual",
        "abort",
    }
