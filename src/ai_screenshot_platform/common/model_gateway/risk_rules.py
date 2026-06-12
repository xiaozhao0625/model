from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ai_screenshot_platform.common.model_gateway.contracts import ActRequest


class RiskRuleDetector:
    risk_terms = {
        "captcha": (
            "captcha",
            "verification code",
            "verify code",
            "验证码",
        ),
        "payment": (
            "payment",
            "pay now",
            "checkout",
            "付款",
            "支付",
        ),
        "recharge": (
            "recharge",
            "top up",
            "充值",
        ),
        "purchase": (
            "purchase",
            "buy now",
            "buy item",
            "购买",
            "下单",
        ),
        "send_chat": (
            "send chat",
            "send message",
            "chat message",
            "发送聊天",
            "发消息",
        ),
        "account_security": (
            "account security",
            "security verification",
            "password reset",
            "账号安全",
            "账户安全",
        ),
        "anti_cheat_bypass": (
            "anti_cheat_bypass",
            "anti cheat bypass",
            "bypass anti cheat",
            "绕过反作弊",
            "反作弊绕过",
        ),
    }

    def detect_act_request(self, request: ActRequest) -> list[str]:
        texts = [
            request.instruction,
            request.scene_class.value,
            *self._flatten_context(request.context),
        ]
        return self.detect_texts(texts)

    def detect_texts(self, texts: Iterable[str]) -> list[str]:
        normalized = "\n".join(text.lower() for text in texts if text)
        detected: list[str] = []
        for risk_flag, terms in self.risk_terms.items():
            if any(term.lower() in normalized for term in terms):
                detected.append(risk_flag)
        return detected

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
