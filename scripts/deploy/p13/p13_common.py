from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]


def base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--machine-name", default=None)
    parser.add_argument("--master-url", default=os.environ.get("MASTER_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--timeout", type=float, default=2.0)
    return parser


def check_tool(name: str, executable: str | None = None) -> dict[str, Any]:
    exe = executable or name
    path = os.environ.get(f"{name.upper()}_PATH") or shutil.which(exe)
    return {
        "name": name,
        "status": "available" if path else "unavailable",
        "path": str(path) if path else None,
    }


def check_python_module(name: str, module: str | None = None) -> dict[str, Any]:
    module_name = module or name
    return {
        "name": name,
        "status": "available" if importlib.util.find_spec(module_name) is not None else "unavailable",
        "module": module_name,
    }


def check_python() -> dict[str, Any]:
    return {"name": "Python", "status": "available", "version": sys.version.split()[0]}


def check_env_present(name: str) -> dict[str, Any]:
    return {"name": name, "status": "available" if bool(os.environ.get(name)) else "unavailable"}


def check_url(name: str, url: str, timeout: float = 2.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {"name": name, "status": "available", "http_status": response.status}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"name": name, "status": "unavailable", "reason": type(exc).__name__}


def check_port(host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"name": f"{host}:{port}", "status": "available"}
    except OSError as exc:
        return {"name": f"{host}:{port}", "status": "unavailable", "reason": type(exc).__name__}


def file_check(name: str, path: str | Path) -> dict[str, Any]:
    target = Path(path)
    return {"name": name, "status": "available" if target.exists() else "missing", "path": str(target)}


def summarize(role: str, machine_name: str, checks: list[dict[str, Any]], recommendations: list[str] | None = None) -> dict[str, Any]:
    available = [item["name"] for item in checks if item.get("status") == "available"]
    unavailable = [item["name"] for item in checks if item.get("status") == "unavailable"]
    skipped = [item["name"] for item in checks if item.get("status") in {"skipped", "missing"}]
    errors = [item for item in checks if item.get("status") == "error"]
    status = "available" if not unavailable and not errors else "needs_attention"
    return {
        "status": status,
        "machine_name": machine_name,
        "role": role,
        "checks": checks,
        "available": available,
        "unavailable": unavailable,
        "skipped": skipped,
        "errors": errors,
        "recommendations": recommendations or [],
        "downloads_performed": False,
        "real_capture_started": False,
    }


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def sanitized_environment_summary() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "node_available": bool(shutil.which("node")),
        "git_available": bool(shutil.which("git")),
        "database_url_configured": bool(os.environ.get("DATABASE_URL")),
        "database_url_value_printed": False,
    }
