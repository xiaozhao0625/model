from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AndroidEmulatorProfile:
    profile_id: str
    emulator_type: str = "generic_adb"
    display_name: str = ""
    adb_serial: str | None = None
    adb_host: str = "127.0.0.1"
    adb_port: int = 5555
    app_package: str = ""
    app_activity: str = ""
    apk_path: str | None = None
    screenshot_method: str = "screencap"
    ui_dump_enabled: bool = True
    ocr_fallback_enabled: bool = False
    snapshot_enabled: bool = False
    notes: str = ""


class AndroidEmulatorProfileLoader:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> list[AndroidEmulatorProfile]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [AndroidEmulatorProfile(**item) for item in payload.get("profiles", [])]
