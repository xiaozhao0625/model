from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class ProviderHealth:
    provider_name: str
    available: bool
    status: str
    reason: str
    model_path: Path


class OptionalModelProvider:
    provider_name = "optional_model"

    def __init__(self, model_path: str | Path, enabled: bool = False) -> None:
        self.model_path = Path(model_path)
        self.enabled = enabled

    def health(self) -> ProviderHealth:
        if not self.enabled:
            return ProviderHealth(
                provider_name=self.provider_name,
                available=False,
                status="disabled",
                reason="provider disabled by runtime config",
                model_path=self.model_path,
            )
        if not self.model_path.exists():
            return ProviderHealth(
                provider_name=self.provider_name,
                available=False,
                status="missing_files",
                reason="model path is missing",
                model_path=self.model_path,
            )
        return ProviderHealth(
            provider_name=self.provider_name,
            available=True,
            status="available",
            reason="model path exists; loading is still explicit",
            model_path=self.model_path,
        )

    def scene_classify(self, request: SceneClassifyRequest) -> SceneClassifyResult:
        return SceneClassifyResult(
            scene_class=SceneClass.UNKNOWN,
            confidence=0.0,
            reason=f"{self.provider_name} unavailable; real model not loaded",
            provider_name=self.provider_name,
        )

    def ground(self, request: GroundRequest) -> GroundResult:
        return GroundResult(
            found=False,
            x=None,
            y=None,
            confidence=0.0,
            reason=f"{self.provider_name} unavailable; real model not loaded",
            provider_name=self.provider_name,
        )

    def act(self, request: ActRequest) -> ActionProposal:
        return ActionProposal(
            action_type=ActionType.REQUEST_MANUAL,
            confidence=0.0,
            reason=f"{self.provider_name} unavailable; request manual review",
            target=None,
            keys=[],
            risk_flags=[],
            provider_name=self.provider_name,
        )
