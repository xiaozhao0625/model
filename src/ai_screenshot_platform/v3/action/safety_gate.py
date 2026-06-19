from __future__ import annotations

from ai_screenshot_platform.v3.schemas import ActionDecision, FusedCandidate


RISK_TERMS = {
    "login",
    "sign in",
    "sign up",
    "register",
    "password",
    "payment",
    "buy",
    "purchase",
    "delete",
    "remove",
    "send",
    "checkout",
    "credit card",
    "captcha",
    "verify",
    "ranked",
    "matchmaking",
    "chat",
    "report",
    "登录",
    "注册",
    "验证码",
    "支付",
    "购买",
    "删除",
    "发送",
    "密码",
    "账号",
    "排位",
    "匹配",
    "聊天",
}


def risk_terms_in_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted(term for term in RISK_TERMS if term in lowered)


class SafetyGate:
    allowed_actions = {"click", "esc", "alt_left", "backspace", "wait", "wasd", "mouse_move_small", "space", "shift_short", "e_or_f_interact_low_frequency"}

    def evaluate(self, action: str, candidate: FusedCandidate | None = None, observe_only: bool = True) -> ActionDecision:
        if action not in self.allowed_actions:
            return ActionDecision(action="wait", allowed=False, reason="action_not_allowed", candidate=candidate)
        if observe_only and action == "click":
            return ActionDecision(action="click", allowed=False, reason="observe_only_blocks_click", candidate=candidate)
        if candidate:
            risks = set(candidate.risk_flags) | set(risk_terms_in_text(candidate.label))
            if risks:
                candidate.blocked = True
                candidate.block_reason = f"risk_terms:{','.join(sorted(risks))}"
                return ActionDecision(action="click", allowed=False, reason=candidate.block_reason, candidate=candidate)
        return ActionDecision(action=action, allowed=True, reason="allowed", candidate=candidate)
