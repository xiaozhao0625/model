from __future__ import annotations

from ai_screenshot_platform.common.model_gateway.contracts import (
    ActionProposal,
    ActionType,
)


class ModelActionSafetyGate:
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
        rejected_action_type: ActionType = ActionType.REQUEST_MANUAL,
    ) -> None:
        if rejected_action_type not in {ActionType.REQUEST_MANUAL, ActionType.ABORT}:
            raise ValueError("rejected_action_type must be request_manual or abort")
        self.rejected_action_type = rejected_action_type

    def validate(self, proposal: ActionProposal) -> ActionProposal:
        blocked_flags = sorted(
            set(proposal.risk_flags).intersection(self.forbidden_risk_flags)
        )
        if not blocked_flags:
            return proposal

        return ActionProposal(
            action_type=self.rejected_action_type,
            confidence=1.0,
            reason=f"blocked forbidden risk flags: {', '.join(blocked_flags)}",
            target=None,
            keys=[],
            risk_flags=list(proposal.risk_flags),
            provider_name=proposal.provider_name,
        )
