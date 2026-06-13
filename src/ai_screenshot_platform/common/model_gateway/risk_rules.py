from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ai_screenshot_platform.common.model_gateway.contracts import ActRequest
from ai_screenshot_platform.common.model_gateway.risk_lexicon import (
    RiskLexicon,
    RiskLexiconLoader,
)


class RiskRuleDetector:
    def __init__(self, lexicon: RiskLexicon | None = None) -> None:
        self.lexicon = lexicon or RiskLexiconLoader.load_default()

    def detect_act_request(self, request: ActRequest) -> list[str]:
        texts = [
            request.instruction,
            request.target_description or "",
            request.scene_class.value,
            *self._flatten_context(request.context),
        ]
        return self.detect_texts(texts)

    def detect_texts(self, texts: Iterable[str]) -> list[str]:
        normalized = "\n".join(text.lower() for text in texts if text)
        detected: list[str] = []
        for risk_flag, terms in self.lexicon.terms_by_risk.items():
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
