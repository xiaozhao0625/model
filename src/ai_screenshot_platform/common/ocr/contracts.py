from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class OcrProviderStatus(StrEnum):
    OK = "ok"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass(frozen=True)
class OcrInput:
    image_path: Path | None = None
    image_bytes: bytes | None = None
    platform_type: str | None = None
    worker_type: str | None = None
    capture_method: str | None = None
    roi: dict[str, int] | None = None
    language_hints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OcrTextBlock:
    text: str
    confidence: float = 1.0
    bbox: tuple[int, int, int, int] | None = None
    language: str | None = None
    source: str = "mock"


@dataclass(frozen=True)
class OcrRiskHit:
    risk_type: str
    matched_text: str
    confidence: float = 1.0
    bbox: tuple[int, int, int, int] | None = None
    action: str = "request_manual"


@dataclass(frozen=True)
class OcrResult:
    provider: str
    available: bool
    status: OcrProviderStatus = OcrProviderStatus.OK
    text_blocks: list[OcrTextBlock] = field(default_factory=list)
    full_text: str = ""
    risk_hits: list[OcrRiskHit] = field(default_factory=list)
    scene_hints: list[str] = field(default_factory=list)
    error_reason: str | None = None
    latency_ms: int = 0


class OcrAdapter:
    provider_name: str

    def run_ocr(self, ocr_input: OcrInput) -> OcrResult:
        raise NotImplementedError
