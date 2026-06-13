from __future__ import annotations

from ai_screenshot_platform.common.ocr.contracts import OcrRiskHit


class OcrActionGuard:
    blocking_risks = {"captcha", "payment", "recharge", "purchase", "account_security", "chat_send"}

    def detect(self, hits: list[OcrRiskHit]) -> list[str]:
        return [hit.risk_type for hit in hits if hit.risk_type in self.blocking_risks]
