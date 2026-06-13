from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDecision:
    detected: bool
    action: str
    reason: str


class PermissionHandler:
    def detect_permission_popup(self, ui_xml: str) -> bool:
        lowered = ui_xml.lower()
        return "permission" in lowered or "allow" in lowered or "允许" in ui_xml

    def handle_permission_popup(self, ui_xml: str, policy: str = "request_manual") -> PermissionDecision:
        detected = self.detect_permission_popup(ui_xml)
        return PermissionDecision(detected, policy if detected else "none", "permission_popup_detected" if detected else "none")

    def detect_permission_popup_by_ocr(self, ocr_result) -> bool:
        return "permission" in ocr_result.full_text.lower() or "权限" in ocr_result.full_text
