from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolHealth:
    name: str
    available: bool
    version: str | None
    reason: str
    required_for: str


def check_python_module(
    module_name: str,
    required_for: str,
    display_name: str | None = None,
) -> ToolHealth:
    name = display_name or module_name
    if importlib.util.find_spec(module_name) is None:
        return ToolHealth(
            name=name,
            available=False,
            version=None,
            reason=f"{module_name} is not installed",
            required_for=required_for,
        )
    return ToolHealth(
        name=name,
        available=True,
        version=None,
        reason="python module is importable",
        required_for=required_for,
    )


def check_command(command_name: str, required_for: str) -> ToolHealth:
    command_path = shutil.which(command_name)
    if command_path is None:
        return ToolHealth(
            name=command_name,
            available=False,
            version=None,
            reason=f"{command_name} command is not available on PATH",
            required_for=required_for,
        )
    return ToolHealth(
        name=command_name,
        available=True,
        version=None,
        reason=f"found at {command_path}",
        required_for=required_for,
    )
