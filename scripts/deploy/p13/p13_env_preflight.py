from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from p13_install_hints import machine_info, role_requirements  # noqa: E402
from p13_report_uploader import upload_report  # noqa: E402


MODULE_BY_NAME = {
    "Playwright Python package": "playwright",
    "pywinauto": "pywinauto",
    "mss": "mss",
    "dxcam": "dxcam",
    "Airtest": "airtest",
    "Appium Python Client": "appium",
}
EXECUTABLE_BY_NAME = {
    "Python": "python",
    "Git": "git",
    "NVIDIA Driver": "nvidia-smi",
    "PostgreSQL psql": "psql",
    "Redis": "redis-cli",
    "Node.js": "node",
    "OBS Studio": "obs64",
    "FFmpeg": "ffmpeg",
    "AutoHotkey": "autohotkey",
    "Android SDK Platform-Tools": "adb",
    "Android Emulator": "emulator",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local P13 environment preflight.")
    parser.add_argument("--role", required=True, choices=["M0", "W1", "W2", "W3"])
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    parser.add_argument("--output-dir", default="runs/p13_preflight")
    parser.add_argument("--topology-file", default="configs/deploy/p13_software_requirements.example.json")
    parser.add_argument("--master-url", default="http://192.168.1.18:8000")
    parser.add_argument("--upload-report", action="store_true")
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()
    report = build_report(args)
    paths = write_report(report, Path(args.output_dir), args.role)
    upload_result = None
    if args.upload_report:
        upload_result = upload_report(paths["report"], args.master_url, args.timeout)
        report["upload"] = upload_result
        paths = write_report(report, Path(args.output_dir), args.role)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root)
    info = machine_info(args.role, project_root / args.topology_file)
    checks = common_checks(project_root, args)
    checks.extend(role_checks(args.role, args, project_root))
    installed = [
        {"name": item["name"], "version": item.get("version", "unknown")}
        for item in checks
        if item["status"] == "installed"
    ]
    missing_required = [
        _missing_entry(item)
        for item in checks
        if item["status"] == "missing" and item.get("severity") == "required"
    ]
    missing_optional = [
        _missing_entry(item)
        for item in checks
        if item["status"] == "missing" and item.get("severity") == "optional"
    ]
    status = "ok"
    if missing_required:
        status = "failed"
    elif missing_optional or any(item["status"] == "warning" for item in checks):
        status = "warning"
    return {
        "role": args.role,
        "machine_name": info["machine_name"],
        "ip": info["ip"],
        "status": status,
        "generated_at": _now(),
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "installed": installed,
        "checks": checks,
        "safe_to_continue": not missing_required,
        "next_step": _next_step(status, args.role),
        "downloads_performed": False,
        "installs_performed": False,
        "remote_commands_executed": False,
        "database_url_value_printed": False,
    }


def common_checks(project_root: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    checks = [
        {"name": "Windows version", "severity": "required", "status": "installed", "version": platform.platform()},
        {"name": "PowerShell", "severity": "required", **_command_status("powershell", ["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.Major"])},
        *_software_checks("common", args, project_root),
        {"name": "GPU model", "severity": "optional", **_command_status("nvidia-smi", ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])},
        {"name": "Disk free space", "severity": "required", **_disk_status(project_root)},
        {"name": "Project directory", "severity": "required", "status": "installed" if project_root.exists() else "missing", "path": str(project_root)},
        {"name": "Virtual environment", "severity": "optional", "status": "installed" if (project_root / ".venv").exists() else "missing", "verify_command": "Test-Path .venv"},
        {"name": "pyproject.toml", "severity": "required", "status": "installed" if (project_root / "pyproject.toml").exists() else "missing"},
        {"name": "package.json", "severity": "required", "status": "installed" if (project_root / "apps/web-console/package.json").exists() else "missing"},
        {"name": ".env", "severity": "required", "status": "installed" if (project_root / ".env").exists() else "missing", "content_printed": False},
        {"name": "p13_local_topology", "severity": "required", "status": "installed" if (project_root / "configs/deploy/p13_software_requirements.example.json").exists() else "missing"},
        {"name": "git commit", "severity": "optional", **_command_status("git commit", ["git", "rev-parse", "--short", "HEAD"], cwd=project_root)},
    ]
    return checks


def role_checks(role: str, args: argparse.Namespace, project_root: Path) -> list[dict[str, Any]]:
    checks = _software_checks(role, args, project_root)
    if role == "M0":
        checks.extend(
            [
                {"name": "DATABASE_URL configured", "severity": "required", "status": "installed" if bool(os.environ.get("DATABASE_URL") or _env_file_value(project_root, "DATABASE_URL")) else "missing", "value_printed": False},
                {"name": "PSQL_PATH configured", "severity": "optional", "status": "installed" if bool(os.environ.get("PSQL_PATH") or _env_file_value(project_root, "PSQL_PATH")) else "missing"},
                {"name": "smoke_postgres_connection.py", "severity": "required", "status": "installed" if (project_root / "scripts/master/smoke_postgres_connection.py").exists() else "missing"},
                {"name": "Master API script", "severity": "required", "status": "installed" if (project_root / "scripts/deploy/p13/start_m0_master_api.bat").exists() else "missing"},
                {"name": "Web Console build ability", "severity": "required", "status": "installed" if (project_root / "apps/web-console/package.json").exists() else "missing"},
                {"name": "Master API reachable", "severity": "optional", **_url_status(args.master_url + "/health", args.timeout)},
            ]
        )
    else:
        checks.extend(
            [
                {"name": "MASTER_URL reachable", "severity": "required", **_url_status(args.master_url + "/health", args.timeout)},
                {"name": "Worker env", "severity": "required", "status": "installed" if (project_root / ".env").exists() else "missing", "content_printed": False},
            ]
        )
    if role == "W1":
        checks.append({"name": "obs-websocket", "severity": "optional", "status": "warning", "reason": "需要在 OBS 内手动启用并确认端口。"})
    if role == "W3":
        checks.append({"name": "adb devices", "severity": "required", **_command_status("adb devices", ["adb", "devices"])})
    return checks


def _software_checks(role: str, args: argparse.Namespace, project_root: Path) -> list[dict[str, Any]]:
    checks = []
    if role == "common":
        requirements = role_requirements("common")
    else:
        requirements = json.loads((project_root / args.topology_file).read_text(encoding="utf-8"))["software"].get(role, [])
    for item in requirements:
        name = item["name"]
        if name in MODULE_BY_NAME:
            installed = importlib.util.find_spec(MODULE_BY_NAME[name]) is not None
            status = "installed" if installed else "missing"
            version = "importable" if installed else None
        elif name == "Playwright browsers":
            status = "warning"
            version = "manual_check_required"
        elif name == "PostgreSQL psql":
            psql_path = os.environ.get("PSQL_PATH") or _env_file_value(project_root, "PSQL_PATH")
            if psql_path and Path(psql_path).exists():
                status = "installed"
                version = str(Path(psql_path))
            else:
                path = shutil.which("psql")
                status = "installed" if path else "missing"
                version = str(path) if path else None
        else:
            command = EXECUTABLE_BY_NAME.get(name, name)
            path = shutil.which(command)
            status = "installed" if path else "missing"
            version = _version_for(command) if path else None
        checks.append({**item, "status": status, "version": version})
    return checks


def write_report(report: dict[str, Any], output_dir: Path, role: str) -> dict[str, Path]:
    role_dir = output_dir / role
    role_dir.mkdir(parents=True, exist_ok=True)
    report_path = role_dir / "preflight_report.json"
    summary_path = role_dir / "preflight_summary.txt"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    summary_path.write_text(_summary_text(report), encoding="utf-8")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    zip_path = role_dir / f"diagnostics_{role}_{timestamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(report_path, arcname="preflight_report.json")
        archive.write(summary_path, arcname="preflight_summary.txt")
    return {"report": report_path, "summary": summary_path, "zip": zip_path}


def _missing_entry(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item["name"],
        "severity": item.get("severity", "required"),
        "install_hint": item.get("install_hint", "按官方文档安装后重新运行预检。"),
        "official_url": item.get("official_url"),
        "verify_command": item.get("verify_command"),
    }


def _summary_text(report: dict[str, Any]) -> str:
    lines = [
        f"P13 环境预检：{report['role']} / {report['status']}",
        f"机器：{report['machine_name']} ({report['ip']})",
        f"可以进入下一步：{report['safe_to_continue']}",
        "",
        "缺失 required：",
    ]
    lines.extend(f"- {item['name']}：{item['install_hint']}" for item in report["missing_required"])
    lines.append("")
    lines.append("下一步：")
    lines.append(report["next_step"])
    return "\n".join(lines) + "\n"


def _next_step(status: str, role: str) -> str:
    if status == "ok":
        return f"{role} required 项已满足，可以进入 M0 总控验收或对应 smoke。"
    if status == "warning":
        return f"{role} required 项基本满足，但 optional/warning 项需要记录原因。"
    return "先安装或配置缺失的 required 软件，再重新运行本脚本。"


def _command_status(name: str, command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    if shutil.which(command[0]) is None:
        return {"status": "missing", "verify_command": " ".join(command)}
    try:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=3, check=False)
    except Exception as exc:
        return {"status": "warning", "reason": type(exc).__name__, "verify_command": " ".join(command)}
    text = (completed.stdout or completed.stderr).strip().splitlines()
    return {"status": "installed" if completed.returncode == 0 else "warning", "version": text[0] if text else "unknown", "verify_command": " ".join(command)}


def _url_status(url: str, timeout: float) -> dict[str, Any]:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {"status": "installed" if response.status < 500 else "warning", "http_status": response.status, "url": url}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": "missing", "reason": type(exc).__name__, "url": url}


def _disk_status(path: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(path.anchor or ".")
    free_gb = round(usage.free / (1024**3), 2)
    return {"status": "installed" if free_gb >= 10 else "warning", "free_gb": free_gb}


def _version_for(command: str) -> str | None:
    result = _command_status(command, [command, "--version"])
    return result.get("version")


def _env_file_value(project_root: Path, name: str) -> str | None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        if key.strip() == name:
            return value.strip()
    return None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


if __name__ == "__main__":
    main()
