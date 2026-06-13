from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AndroidDeviceInfo:
    serial: str
    state: str = "unknown"
