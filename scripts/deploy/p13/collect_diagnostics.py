from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FILES = [
    "machine_ready.json",
    "worker_ready.json",
    "tool_health.json",
    "android_runtime.json",
    "quality_report.json",
    "ocr_report.json",
    "smoke_report.json",
    "run.log",
    "worker.log",
    "master.log",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect P13 diagnostics without secrets.")
    parser.add_argument("--machine", required=True, choices=["M0", "W1", "W2", "W3"])
    parser.add_argument("--source", default="runs")
    parser.add_argument("--output", default="runs/diagnostics")
    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"diagnostics_{args.machine}.zip"
    manifest: dict[str, object] = {
        "machine": args.machine,
        "missing": [],
        "included": [],
        "secrets_included": False,
        "database_url_printed": False,
    }
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _write_json(archive, "environment_summary.json", _environment_summary())
        source_root = Path(args.source)
        for name in DEFAULT_FILES:
            path = source_root / name
            if path.exists() and path.is_file():
                archive.write(path, arcname=name)
                manifest["included"].append(name)  # type: ignore[index]
            else:
                manifest["missing"].append(name)  # type: ignore[index]
        _write_json(archive, "diagnostics_manifest.json", manifest)
    print(json.dumps({"status": "ok", "zip_path": str(zip_path), **manifest}, ensure_ascii=False, indent=2))


def _environment_summary() -> dict[str, object]:
    return {
        "python_version": platform.python_version(),
        "node_version": _command_version(["node", "--version"]),
        "git_commit": _command_version(["git", "rev-parse", "--short", "HEAD"]),
        "nvidia_smi": _command_version(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"], timeout=3),
        "database_url_configured": False,
        "database_url_value_printed": False,
    }


def _command_version(command: list[str], timeout: int = 2) -> str:
    if shutil.which(command[0]) is None:
        return "unavailable"
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except Exception as exc:  # pragma: no cover - depends on host tools
        return f"unavailable:{type(exc).__name__}"
    text = (completed.stdout or completed.stderr).strip().splitlines()
    return text[0] if text else "unknown"


def _write_json(archive: zipfile.ZipFile, name: str, payload: dict[str, object]) -> None:
    archive.writestr(name, json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
