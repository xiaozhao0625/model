from __future__ import annotations

from typing import Any


def ok(data: Any, message: str = "ok") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data}


def error(message: str, code: int = 1) -> dict[str, Any]:
    return {"code": code, "message": message, "data": None}
