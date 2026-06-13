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
from ai_screenshot_platform.common.model_gateway.mock_provider import (
    MockModelGatewayProvider,
)
from ai_screenshot_platform.common.model_gateway.provider_config import (
    ProviderConfig,
    ProviderType,
)
from ai_screenshot_platform.common.model_gateway.provider_registry import (
    ProviderCapabilityError,
)


class BaseStubProvider:
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def scene_classify(
        self,
        request: SceneClassifyRequest,
    ) -> SceneClassifyResult:
        raise ProviderCapabilityError(
            f"provider {self.provider_name} does not support scene_classify"
        )

    def ground(self, request: GroundRequest) -> GroundResult:
        raise ProviderCapabilityError(
            f"provider {self.provider_name} does not support ground"
        )

    def act(self, request: ActRequest) -> ActionProposal:
        raise ProviderCapabilityError(
            f"provider {self.provider_name} does not support act"
        )


class UITarsStubProvider(BaseStubProvider):
    def act(self, request: ActRequest) -> ActionProposal:
        return ActionProposal(
            action_type=ActionType.REQUEST_MANUAL,
            confidence=0.0,
            reason="ui_tars stub does not call a real model",
            target=None,
            keys=[],
            risk_flags=[],
            provider_name=self.provider_name,
        )


class ShowUIStubProvider(BaseStubProvider):
    def ground(self, request: GroundRequest) -> GroundResult:
        return GroundResult(
            found=False,
            x=None,
            y=None,
            confidence=0.0,
            reason="showui stub does not call a real model",
            provider_name=self.provider_name,
        )


class QwenVLStubProvider(BaseStubProvider):
    def scene_classify(
        self,
        request: SceneClassifyRequest,
    ) -> SceneClassifyResult:
        return SceneClassifyResult(
            scene_class=SceneClass.UNKNOWN,
            confidence=0.0,
            reason="qwen-vl stub does not call a real model",
            provider_name=self.provider_name,
        )


class OmniParserStubProvider(BaseStubProvider):
    def ground(self, request: GroundRequest) -> GroundResult:
        return GroundResult(
            found=False,
            x=None,
            y=None,
            confidence=0.0,
            reason="omniparser stub does not call a real model",
            provider_name=self.provider_name,
        )


def create_stub_provider(config: ProviderConfig):
    if config.provider_type == ProviderType.MOCK:
        provider = MockModelGatewayProvider()
        provider.provider_name = config.provider_name
        return provider
    if config.provider_type == ProviderType.UI_TARS:
        return UITarsStubProvider(config.provider_name)
    if config.provider_type == ProviderType.SHOWUI:
        return ShowUIStubProvider(config.provider_name)
    if config.provider_type == ProviderType.QWEN_VL:
        return QwenVLStubProvider(config.provider_name)
    if config.provider_type == ProviderType.OMNIPARSER:
        return OmniParserStubProvider(config.provider_name)
    return BaseStubProvider(config.provider_name)
