import json
from pathlib import Path

import pytest

from ai_screenshot_platform.common.model_gateway.contracts import (
    ActRequest,
    ActionProposal,
    ActionType,
    GroundRequest,
    GroundResult,
    SceneClass,
    SceneClassifyRequest,
    SceneClassifyResult,
)
from ai_screenshot_platform.common.model_gateway.gateway_service import (
    ModelGatewayService,
)
from ai_screenshot_platform.common.model_gateway.mock_provider import (
    MockModelGatewayProvider,
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_act_request(
    instruction: str = "click the continue button",
    context: dict | None = None,
    scene_class: SceneClass = SceneClass.MENU,
) -> ActRequest:
    return ActRequest(
        app_id="demo_app",
        run_id="demo_run",
        screenshot_path="runs/demo/screen.webp",
        scene_class=scene_class,
        instruction=instruction,
        context=context or {},
    )


class CountingProvider:
    provider_name = "counting"

    def __init__(self, risk_flags: list[str] | None = None) -> None:
        self.act_calls = 0
        self.risk_flags = risk_flags or []

    def scene_classify(
        self,
        request: SceneClassifyRequest,
    ) -> SceneClassifyResult:
        return SceneClassifyResult(
            scene_class=SceneClass.MENU,
            confidence=1.0,
            reason="counting scene",
            provider_name=self.provider_name,
        )

    def ground(self, request: GroundRequest) -> GroundResult:
        return GroundResult(
            found=True,
            x=10,
            y=20,
            confidence=1.0,
            reason="counting ground",
            provider_name=self.provider_name,
        )

    def act(self, request: ActRequest) -> ActionProposal:
        self.act_calls += 1
        return ActionProposal(
            action_type=ActionType.CLICK,
            confidence=0.9,
            reason="counting action",
            target={"x": 10, "y": 20},
            keys=[],
            risk_flags=self.risk_flags,
            provider_name=self.provider_name,
        )


def test_service_can_call_scene_classify(tmp_path):
    service = ModelGatewayService(MockModelGatewayProvider(), audit_log_dir=tmp_path)
    request = SceneClassifyRequest(
        app_id="demo_app",
        run_id="demo_run",
        screenshot_path="runs/demo/screen.webp",
        context={"mock_scene_class": SceneClass.DOCUMENT.value},
    )

    result = service.scene_classify(request)

    assert result.scene_class == SceneClass.DOCUMENT
    assert result.provider_name == "mock"


def test_service_can_call_ground(tmp_path):
    service = ModelGatewayService(
        MockModelGatewayProvider(mock_x=5, mock_y=7),
        audit_log_dir=tmp_path,
    )
    request = GroundRequest(
        app_id="demo_app",
        run_id="demo_run",
        screenshot_path="runs/demo/screen.webp",
        target_description="continue button",
        context={},
    )

    result = service.ground(request)

    assert result.found is True
    assert result.x == 5
    assert result.y == 7


def test_service_can_call_safe_act(tmp_path):
    service = ModelGatewayService(CountingProvider(), audit_log_dir=tmp_path)

    proposal = service.act(make_act_request())

    assert proposal.action_type == ActionType.CLICK
    assert proposal.risk_flags == []


@pytest.mark.parametrize(
    ("instruction", "risk_flag"),
    [
        ("solve this captcha and continue", "captcha"),
        ("open payment and pay now", "payment"),
        ("purchase this item", "purchase"),
        ("send chat message hello", "send_chat"),
    ],
)
def test_instruction_risks_are_blocked_without_provider_flags(
    tmp_path,
    instruction,
    risk_flag,
):
    provider = CountingProvider()
    service = ModelGatewayService(provider, audit_log_dir=tmp_path)

    proposal = service.act(make_act_request(instruction=instruction))

    assert proposal.action_type in {ActionType.REQUEST_MANUAL, ActionType.ABORT}
    assert risk_flag in proposal.risk_flags
    assert provider.act_calls == 0


def test_context_anti_cheat_bypass_is_blocked(tmp_path):
    service = ModelGatewayService(CountingProvider(), audit_log_dir=tmp_path)

    proposal = service.act(
        make_act_request(context={"requested_mode": "anti_cheat_bypass"})
    )

    assert proposal.action_type in {ActionType.REQUEST_MANUAL, ActionType.ABORT}
    assert "anti_cheat_bypass" in proposal.risk_flags


def test_provider_risk_flags_are_blocked(tmp_path):
    service = ModelGatewayService(
        CountingProvider(risk_flags=["purchase"]),
        audit_log_dir=tmp_path,
    )

    proposal = service.act(make_act_request())

    assert proposal.action_type in {ActionType.REQUEST_MANUAL, ActionType.ABORT}
    assert "purchase" in proposal.risk_flags


def test_safe_act_is_not_falsely_blocked(tmp_path):
    service = ModelGatewayService(CountingProvider(), audit_log_dir=tmp_path)

    proposal = service.act(
        make_act_request(instruction="click the visible continue button")
    )

    assert proposal.action_type == ActionType.CLICK
    assert proposal.reason == "counting action"


def test_act_writes_model_gateway_log(tmp_path):
    service = ModelGatewayService(CountingProvider(), audit_log_dir=tmp_path)

    service.act(make_act_request())

    assert service.audit_log_path.is_file()


def test_audit_log_is_valid_jsonl(tmp_path):
    service = ModelGatewayService(CountingProvider(), audit_log_dir=tmp_path)
    service.act(make_act_request())
    service.act(make_act_request(instruction="solve captcha"))

    entries = read_jsonl(service.audit_log_path)

    assert len(entries) == 2
    for entry in entries:
        assert set(entry) == {
            "timestamp",
            "app_id",
            "run_id",
            "task_type",
            "provider_name",
            "input_risk_flags",
            "output_risk_flags",
            "final_action_type",
            "blocked",
            "reason",
        }
        assert entry["task_type"] == "act"
        assert entry["provider_name"] == "counting"
    assert entries[0]["blocked"] is False
    assert entries[1]["blocked"] is True
