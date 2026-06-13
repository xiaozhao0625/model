from __future__ import annotations

from dataclasses import dataclass, field

from ai_screenshot_platform.common.ocr.contracts import OcrResult


@dataclass(frozen=True)
class OcrQualityDecision:
    reject: bool = False
    reject_reason: str | None = None
    ocr_text_detected: bool = False
    ocr_risk_hits: list[dict] = field(default_factory=list)
    ocr_risk_hit_count: int = 0
    ocr_confidence: float = 0.0
    ocr_provider: str = "disabled"
    ocr_unavailable_reason: str | None = None
    ocr_scene_hints: list[str] = field(default_factory=list)
    browser_chrome_visible: bool = False


class OcrDangerousPageDetector:
    rejecting_risks = {"captcha", "payment", "recharge", "purchase", "account_security", "chat_send"}

    def detect(self, result: OcrResult) -> OcrQualityDecision:
        risky = [hit for hit in result.risk_hits if hit.risk_type in self.rejecting_risks]
        return OcrQualityDecision(
            reject=bool(risky),
            reject_reason="dangerous_page" if risky else None,
            ocr_text_detected=bool(result.full_text),
            ocr_risk_hits=[hit.__dict__ for hit in result.risk_hits],
            ocr_risk_hit_count=len(result.risk_hits),
            ocr_confidence=max([block.confidence for block in result.text_blocks] or [0.0]),
            ocr_provider=result.provider,
            ocr_unavailable_reason=None if result.available else (result.error_reason or "ocr_unavailable"),
            ocr_scene_hints=result.scene_hints,
            browser_chrome_visible=OcrBrowserChromeDetector().detect(result),
        )


class OcrBrowserChromeDetector:
    terms = ["http://", "https://", "标签页", "地址栏", "new tab", "address bar"]

    def detect(self, result: OcrResult) -> bool:
        text = result.full_text.lower()
        return any(term.lower() in text for term in self.terms)


class OcrWrongWindowHint:
    def detect(self, result: OcrResult, expected_title: str | None = None) -> bool:
        if not expected_title or not result.full_text:
            return False
        return expected_title.lower() not in result.full_text.lower()


class OcrQualityGate:
    def evaluate(self, result: OcrResult) -> OcrQualityDecision:
        if not result.available:
            return OcrQualityDecision(
                ocr_provider=result.provider,
                ocr_unavailable_reason=result.error_reason or "ocr_unavailable",
            )
        return OcrDangerousPageDetector().detect(result)
