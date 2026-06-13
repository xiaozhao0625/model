from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai_screenshot_platform.common.ocr.contracts import OcrRiskHit


DEFAULT_RISK_TERMS: dict[str, list[str]] = {
    "captcha": ["captcha", "verification", "verification code", "验证码", "人机验证", "安全验证", "滑块验证"],
    "payment": ["payment", "pay", "checkout", "confirm payment", "支付", "付款", "收银台", "确认支付"],
    "recharge": ["recharge", "top up", "充值"],
    "purchase": ["purchase", "buy", "order", "购买", "下单", "订单"],
    "account_security": ["account security", "password", "账号安全", "登录验证", "改密码", "绑定手机"],
    "chat_send": ["send chat", "chat message", "send", "chat", "发送聊天", "发消息", "私聊", "聊天"],
    "login_sensitive": ["login", "登录", "手机号登录", "密码登录"],
    "phone_verification": ["phone verification", "sms code", "手机验证", "短信验证码"],
    "anti_cheat_warning": ["anti-cheat", "anti cheat", "反作弊", "检测警告"],
}


RISK_ACTIONS = {
    "captcha": "request_manual",
    "payment": "reject",
    "recharge": "reject",
    "purchase": "reject",
    "account_security": "request_manual",
    "chat_send": "block_action",
    "login_sensitive": "request_manual",
    "phone_verification": "request_manual",
    "anti_cheat_warning": "request_manual",
}


@dataclass(frozen=True)
class OcrRiskLexicon:
    terms: dict[str, list[str]]
    max_snippet_length: int = 32

    @classmethod
    def default(cls) -> OcrRiskLexicon:
        return cls(DEFAULT_RISK_TERMS)

    @classmethod
    def from_json(cls, path: str | Path) -> OcrRiskLexicon:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        terms = payload.get("risk_terms", payload)
        return cls({str(key): [str(item) for item in value] for key, value in terms.items()})

    def detect(self, text: str) -> list[OcrRiskHit]:
        normalized = text.lower()
        hits: list[OcrRiskHit] = []
        for risk_type, terms in self.terms.items():
            for term in terms:
                if term.lower() in normalized:
                    hits.append(
                        OcrRiskHit(
                            risk_type=risk_type,
                            matched_text=term[: self.max_snippet_length],
                            action=RISK_ACTIONS.get(risk_type, "request_manual"),
                        )
                    )
                    break
        return hits
