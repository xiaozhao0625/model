from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ai_screenshot_platform.common.behavior.contracts import (
    BehaviorAction,
    BehaviorActionType,
    BehaviorPack,
    BehaviorSafetyDecision,
)


class BehaviorSafetyGate:
    forbidden_risk_flags = frozenset(
        {
            "captcha",
            "payment",
            "recharge",
            "purchase",
            "send_chat",
            "account_security",
            "anti_cheat_bypass",
        }
    )

    def __init__(
        self,
        rejected_action_type: BehaviorActionType = BehaviorActionType.REQUEST_MANUAL,
    ) -> None:
        if rejected_action_type not in {
            BehaviorActionType.REQUEST_MANUAL,
            BehaviorActionType.ABORT,
        }:
            raise ValueError("rejected_action_type must be request_manual or abort")
        self.rejected_action_type = rejected_action_type

    def validate(
        self,
        pack: BehaviorPack,
        action: BehaviorAction,
        context: Iterable[Any] | None = None,
    ) -> BehaviorSafetyDecision:
        context_text = "\n".join(self._flatten_context(context)).lower()
        forbidden_matches = sorted(
            forbidden
            for forbidden in pack.forbidden_context
            if forbidden and forbidden.lower() in context_text
        )
        risk_matches = sorted(
            set(action.risk_flags).intersection(self.forbidden_risk_flags)
        )
        blocked_flags = sorted(set(forbidden_matches + risk_matches))
        if blocked_flags:
            return BehaviorSafetyDecision(
                action_type=self.rejected_action_type,
                blocked=True,
                reason=f"blocked forbidden behavior risk: {', '.join(blocked_flags)}",
                risk_flags=blocked_flags,
            )

        return BehaviorSafetyDecision(
            action_type=action.action_type,
            blocked=False,
            reason="allowed",
            risk_flags=list(action.risk_flags),
        )

    def _flatten_context(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, dict):
            texts: list[str] = []
            for key, item in value.items():
                texts.extend(self._flatten_context(key))
                texts.extend(self._flatten_context(item))
            return texts
        if isinstance(value, (list, tuple, set)):
            texts = []
            for item in value:
                texts.extend(self._flatten_context(item))
            return texts
        return [str(value)]
