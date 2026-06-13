from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    default_provider: str
    fallback_provider: str
    enabled_providers: list[str] = field(default_factory=list)
    provider_timeouts: dict[str, int] = field(default_factory=dict)
    max_loaded_models: int = 1
    allow_gpu: bool = False
    allow_cpu_fallback: bool = True
    audit_log_dir: str | Path = "runs/model_gateway_audit"


class ProviderRuntimeConfigLoader:
    @classmethod
    def load(cls, path: str | Path) -> ProviderRuntimeConfig:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProviderRuntimeConfig:
        return ProviderRuntimeConfig(
            default_provider=str(payload.get("default_provider", "mock")),
            fallback_provider=str(payload.get("fallback_provider", "mock")),
            enabled_providers=[str(item) for item in payload.get("enabled_providers", ["mock"])],
            provider_timeouts=dict(payload.get("provider_timeouts", {})),
            max_loaded_models=int(payload.get("max_loaded_models", 1)),
            allow_gpu=bool(payload.get("allow_gpu", False)),
            allow_cpu_fallback=bool(payload.get("allow_cpu_fallback", True)),
            audit_log_dir=payload.get("audit_log_dir", "runs/model_gateway_audit"),
        )
