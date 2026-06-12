from __future__ import annotations

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


class MockModelGatewayProvider:
    provider_name = "mock"

    def __init__(
        self,
        mock_scene_class: SceneClass = SceneClass.UNKNOWN,
        mock_found: bool = True,
        mock_x: int = 0,
        mock_y: int = 0,
        mock_action_type: ActionType = ActionType.NO_OP,
    ) -> None:
        self.mock_scene_class = mock_scene_class
        self.mock_found = mock_found
        self.mock_x = mock_x
        self.mock_y = mock_y
        self.mock_action_type = mock_action_type

    def scene_classify(
        self,
        request: SceneClassifyRequest,
    ) -> SceneClassifyResult:
        scene_class = self._scene_class_from_context(request)
        return SceneClassifyResult(
            scene_class=scene_class,
            confidence=1.0 if scene_class != SceneClass.UNKNOWN else 0.5,
            reason="mock scene classification",
            provider_name=self.provider_name,
        )

    def ground(self, request: GroundRequest) -> GroundResult:
        x = int(request.context.get("mock_x", self.mock_x))
        y = int(request.context.get("mock_y", self.mock_y))
        found = bool(request.context.get("mock_found", self.mock_found))
        return GroundResult(
            found=found,
            x=x if found else None,
            y=y if found else None,
            confidence=1.0 if found else 0.0,
            reason="mock grounding result",
            provider_name=self.provider_name,
        )

    def act(self, request: ActRequest) -> ActionProposal:
        action_type = ActionType(
            request.context.get("mock_action_type", self.mock_action_type.value)
        )
        risk_flags = list(request.context.get("mock_risk_flags", []))
        return ActionProposal(
            action_type=action_type,
            confidence=1.0,
            reason="mock action proposal",
            target=request.context.get("mock_target"),
            keys=list(request.context.get("mock_keys", [])),
            risk_flags=risk_flags,
            provider_name=self.provider_name,
        )

    def _scene_class_from_context(self, request: SceneClassifyRequest) -> SceneClass:
        value = request.context.get("mock_scene_class", self.mock_scene_class.value)
        return SceneClass(value)
