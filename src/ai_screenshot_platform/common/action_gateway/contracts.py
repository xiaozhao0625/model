from __future__ import annotations

from dataclasses import dataclass, field

from ai_screenshot_platform.common.ocr.contracts import OcrRiskHit


@dataclass(frozen=True)
class ActionGatewayRequest:
    action_type: str
    instruction: str = ""
    target: dict | None = None
    risk_flags: list[str] = field(default_factory=list)
    ocr_risk_hits: list[OcrRiskHit] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ActionGatewayDecision:
    allowed: bool
    final_action: str
    blocked_by: str | None = None
    risk_flags: list[str] = field(default_factory=list)
    reason: str = ""
