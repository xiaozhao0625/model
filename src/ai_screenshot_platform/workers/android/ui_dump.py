from __future__ import annotations

import xml.etree.ElementTree as ET

from ai_screenshot_platform.workers.android.adb_runtime import AdbRuntime


class UiDumpReader:
    def __init__(self, runtime: AdbRuntime | None = None) -> None:
        self.runtime = runtime or AdbRuntime()

    def dump_ui_xml(self, serial: str):
        return self.runtime.uiautomator_dump(serial)

    def parse_clickable_nodes(self, xml: str) -> list[dict]:
        root = ET.fromstring(xml)
        return [node.attrib for node in root.iter() if node.attrib.get("clickable") == "true"]

    def detect_permission_popup(self, xml: str) -> bool:
        lowered = xml.lower()
        return "permission" in lowered or "允许" in xml

    def detect_dangerous_nodes(self, xml: str) -> list[str]:
        lowered = xml.lower()
        terms = ["payment", "captcha", "account", "chat", "send", "支付", "验证码", "账号", "聊天"]
        return [term for term in terms if term in lowered]
