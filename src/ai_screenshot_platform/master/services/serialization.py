from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any


def to_api_data(value: Any) -> Any:
    if is_dataclass(value):
        return to_api_data(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: to_api_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_api_data(item) for item in value]
    return value
