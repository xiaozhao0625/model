from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.behavior.contracts import (
    BehaviorAction,
    BehaviorActionType,
    BehaviorPack,
    BehaviorPackError,
    GameType,
)
from ai_screenshot_platform.common.domain.buckets import Bucket


class BehaviorPackLoader:
    required_pack_fields = frozenset(
        {
            "pack_id",
            "game_type",
            "version",
            "status",
            "allowed_context",
            "forbidden_context",
            "capture_bucket",
            "record_then_extract",
            "actions",
        }
    )
    required_action_fields = frozenset(
        {
            "action_id",
            "action_type",
            "description",
            "duration_ms",
            "bucket",
            "risk_flags",
            "params",
        }
    )

    @classmethod
    def load(cls, path: str | Path) -> BehaviorPack:
        resolved_path = Path(path).resolve()
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise BehaviorPackError("behavior pack must be a JSON object")
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> BehaviorPack:
        missing = cls.required_pack_fields - set(payload)
        if missing:
            raise BehaviorPackError(
                "behavior pack missing required fields: "
                + ", ".join(sorted(missing))
            )

        actions_payload = payload["actions"]
        if not isinstance(actions_payload, list) or not actions_payload:
            raise BehaviorPackError("behavior pack actions must be a non-empty list")

        return BehaviorPack(
            pack_id=str(payload["pack_id"]),
            game_type=GameType(str(payload["game_type"])),
            version=str(payload["version"]),
            status=str(payload["status"]),
            allowed_context=cls._string_list(payload["allowed_context"], "allowed_context"),
            forbidden_context=cls._string_list(
                payload["forbidden_context"], "forbidden_context"
            ),
            capture_bucket=Bucket(str(payload["capture_bucket"])),
            record_then_extract=bool(payload["record_then_extract"]),
            actions=[cls._load_action(action) for action in actions_payload],
        )

    @classmethod
    def _load_action(cls, payload: Any) -> BehaviorAction:
        if not isinstance(payload, dict):
            raise BehaviorPackError("behavior action must be a JSON object")
        missing = cls.required_action_fields - set(payload)
        if missing:
            raise BehaviorPackError(
                "behavior action missing required fields: "
                + ", ".join(sorted(missing))
            )

        return BehaviorAction(
            action_id=str(payload["action_id"]),
            action_type=BehaviorActionType(str(payload["action_type"])),
            description=str(payload["description"]),
            duration_ms=int(payload["duration_ms"]),
            bucket=Bucket(str(payload["bucket"])) if payload["bucket"] is not None else None,
            risk_flags=cls._string_list(payload["risk_flags"], "risk_flags"),
            params=cls._dict(payload["params"], "params"),
        )

    @staticmethod
    def _string_list(value: Any, field_name: str) -> list[str]:
        if not isinstance(value, list):
            raise BehaviorPackError(f"{field_name} must be a list")
        return [str(item) for item in value]

    @staticmethod
    def _dict(value: Any, field_name: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise BehaviorPackError(f"{field_name} must be an object")
        return dict(value)
