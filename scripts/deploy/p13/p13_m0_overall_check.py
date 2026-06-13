from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from p13_install_hints import topology  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run P13 M0 overall acceptance check.")
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    parser.add_argument("--topology-file", default="configs/deploy/p13_software_requirements.example.json")
    parser.add_argument("--output-dir", default="runs/p13_overall")
    parser.add_argument("--master-url", default="http://192.168.1.18:8000")
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()
    summary = build_summary(args)
    write_outputs(summary, Path(args.output_dir))
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root)
    topo = topology(project_root / args.topology_file)
    machines = {
        key.lower(): {"ip": value["ip"], "machine_name": value["machine_name"], "status": "unknown"}
        for key, value in topo["machines"].items()
    }
    warnings: list[str] = []
    blocking_errors: list[str] = []
    next_actions: list[str] = []

    master_health = _get_json(args.master_url.rstrip("/") + "/health", args.timeout)
    if not master_health["ok"]:
        blocking_errors.append("M0 Master API /health 不可访问。")
        next_actions.append("在 M0 启动 Master API 后重新运行 p13_m0_overall_check.ps1。")
    machines["m0"]["status"] = "ok" if master_health["ok"] else "failed"

    database = _postgres_smoke(project_root)
    if database.get("status") != "ok":
        warnings.append("PostgreSQL smoke 未通过或未配置。")
        next_actions.append("在 M0 运行 python scripts/master/smoke_postgres_connection.py。")

    network = {}
    if args.skip_network:
        network["status"] = "skipped"
    else:
        network = _network_checks(topo, args.timeout)
        for name, item in network.items():
            if isinstance(item, dict) and item.get("status") == "unavailable":
                warnings.append(f"{name} 网络不可达。")

    workers = _api_data(args.master_url, "/api/workers", [], args.timeout)
    worker_index = {str(item.get("worker_id", "")).lower(): item for item in workers if isinstance(item, dict)}
    for role in ["w1", "w2", "w3"]:
        if not any(role in worker_id for worker_id in worker_index):
            warnings.append(f"{role.upper()} 未在 Master API 注册或未匹配到心跳。")
            next_actions.append(f"在 {role.upper()} 运行 p13_env_preflight.ps1 或启动对应 Worker。")
            machines[role]["status"] = "warning"
        else:
            machines[role]["status"] = "ok"

    tool_health = _api_data(args.master_url, "/api/tool-health", {}, args.timeout)
    diagnostics = _api_data(args.master_url, "/api/diagnostics", [], args.timeout)
    quality_reports = _api_data(args.master_url, "/api/quality-reports", [], args.timeout)
    ocr_reports = _api_data(args.master_url, "/api/ocr/reports", [], args.timeout)
    behavior_candidates = _api_data(args.master_url, "/api/behavior-candidates", [], args.timeout)

    smoke = _smoke_status(project_root, args.skip_smoke)
    if smoke.get("missing_smoke"):
        warnings.append("四类 smoke 或四机联动 smoke 尚未全部完成。")
        next_actions.append("按 docs/deployment/p13_smoke_test_plan.md 运行对应 smoke。")

    status = "ok"
    if blocking_errors:
        status = "failed"
    elif warnings:
        status = "warning"

    return {
        "status": status,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "master_url": args.master_url,
        "machines": machines,
        "network": network,
        "workers": {"count": len(workers), "items": workers},
        "database": database,
        "tool_health": tool_health,
        "diagnostics": {"count": len(diagnostics) if isinstance(diagnostics, list) else 0, "items": diagnostics},
        "quality_reports": {"count": len(quality_reports) if isinstance(quality_reports, list) else 0},
        "ocr_reports": {"count": len(ocr_reports) if isinstance(ocr_reports, list) else 0},
        "behavior_candidates": {"count": len(behavior_candidates) if isinstance(behavior_candidates, list) else 0},
        "smoke": smoke,
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "next_actions": next_actions,
        "remote_commands_executed": False,
        "database_url_value_printed": False,
    }


def write_outputs(summary: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "overall_summary.json"
    error_path = output_dir / "overall_error_report.txt"
    zip_path = output_dir / "p13_overall_diagnostics.zip"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    error_path.write_text(_error_report(summary), encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(summary_path, arcname="overall_summary.json")
        archive.write(error_path, arcname="overall_error_report.txt")


def _error_report(summary: dict[str, Any]) -> str:
    lines = [f"P13 四机总控验收结果：{summary['status']}", "", "阻塞问题："]
    if summary["blocking_errors"]:
        lines.extend(f"{index}. {item}" for index, item in enumerate(summary["blocking_errors"], start=1))
    else:
        lines.append("无阻塞问题。")
    lines.append("")
    lines.append("警告：")
    if summary["warnings"]:
        lines.extend(f"{index}. {item}" for index, item in enumerate(summary["warnings"], start=1))
    else:
        lines.append("无警告。")
    lines.append("")
    lines.append("建议下一步：")
    if summary["next_actions"]:
        lines.extend(f"{index}. {item}" for index, item in enumerate(summary["next_actions"], start=1))
    else:
        lines.append("继续执行 P13 smoke 验收清单。")
    return "\n".join(lines) + "\n"


def _postgres_smoke(project_root: Path) -> dict[str, Any]:
    script = project_root / "scripts/master/smoke_postgres_connection.py"
    if not script.exists():
        return {"status": "missing", "schema_ready": False}
    completed = subprocess.run([sys.executable, str(script)], cwd=project_root, capture_output=True, text=True, timeout=10, check=False)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "unavailable", "schema_ready": False}
    return {key: payload.get(key) for key in ["status", "postgres_available", "schema_ready", "tables_checked"]}


def _network_checks(topo: dict[str, Any], timeout: float) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for role in ["W1", "W2", "W3"]:
        ip = topo["machines"][role]["ip"]
        checks[role.lower()] = _tcp_check(ip, 8000, timeout)
    return checks


def _tcp_check(host: str, port: int, timeout: float) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ip": host, "port": port, "status": "available"}
    except OSError as exc:
        return {"ip": host, "port": port, "status": "unavailable", "reason": type(exc).__name__}


def _api_data(master_url: str, path: str, fallback: Any, timeout: float) -> Any:
    result = _get_json(master_url.rstrip("/") + path, timeout)
    if not result["ok"]:
        return fallback
    payload = result["payload"]
    if isinstance(payload, dict) and payload.get("ok") is True:
        return payload.get("data", fallback)
    if isinstance(payload, dict) and payload.get("code") == 0:
        return payload.get("data", fallback)
    return fallback


def _get_json(url: str, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {"ok": True, "http_status": response.status, "payload": json.loads(response.read().decode("utf-8"))}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "reason": type(exc).__name__}


def _smoke_status(project_root: Path, skip_smoke: bool) -> dict[str, Any]:
    if skip_smoke:
        return {"status": "skipped", "missing_smoke": True, "recommendation": "取消 --skip-smoke 后根据 smoke_report 文件判断。"}
    expected = ["m0_smoke_report.json", "w1_smoke_report.json", "w2_smoke_report.json", "w3_smoke_report.json", "four_machine_smoke_report.json"]
    present = [name for name in expected if (project_root / "runs" / name).exists()]
    return {
        "status": "ok" if len(present) == len(expected) else "warning",
        "present": present,
        "missing": [name for name in expected if name not in present],
        "missing_smoke": len(present) != len(expected),
        "recommendation": "在对应机器运行 p13 smoke 后汇总到 M0。",
    }


if __name__ == "__main__":
    main()
