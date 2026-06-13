from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class RiskLexiconError(ValueError):
    pass


@dataclass(frozen=True)
class RiskLexicon:
    terms_by_risk: dict[str, tuple[str, ...]]

    def risk_types(self) -> set[str]:
        return set(self.terms_by_risk)

    def terms_for(self, risk_type: str) -> tuple[str, ...]:
        return self.terms_by_risk.get(risk_type, ())


class RiskLexiconLoader:
    required_risk_types = frozenset(
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

    @classmethod
    def load_default(cls) -> RiskLexicon:
        return cls.load(cls.default_path())

    @classmethod
    def load(cls, path: str | Path) -> RiskLexicon:
        resolved_path = Path(path).resolve()
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RiskLexiconError("risk lexicon must be a JSON object")

        missing = cls.required_risk_types - set(payload)
        if missing:
            raise RiskLexiconError(
                "risk lexicon missing required risk types: "
                + ", ".join(sorted(missing))
            )

        terms_by_risk: dict[str, tuple[str, ...]] = {}
        for risk_type, terms in payload.items():
            if not isinstance(terms, list) or not terms:
                raise RiskLexiconError(
                    f"risk lexicon entry must be a non-empty list: {risk_type}"
                )
            terms_by_risk[str(risk_type)] = tuple(str(term) for term in terms)
        return RiskLexicon(terms_by_risk=terms_by_risk)

    @classmethod
    def default_path(cls) -> Path:
        return (
            Path(__file__).resolve().parents[4]
            / "configs"
            / "safety"
            / "risk_lexicon.json"
        )
