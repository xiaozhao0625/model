from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REQUIREMENTS = REPO_ROOT / "configs" / "deploy" / "p13_software_requirements.example.json"


def load_requirements(path: str | Path = DEFAULT_REQUIREMENTS) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def role_requirements(role: str, path: str | Path = DEFAULT_REQUIREMENTS) -> list[dict[str, Any]]:
    payload = load_requirements(path)
    if role == "common":
        return list(payload["software"]["common"])
    return [*payload["software"]["common"], *payload["software"].get(role, [])]


def topology(path: str | Path = DEFAULT_REQUIREMENTS) -> dict[str, Any]:
    return load_requirements(path)["topology"]


def machine_info(role: str, path: str | Path = DEFAULT_REQUIREMENTS) -> dict[str, Any]:
    return topology(path)["machines"][role]
