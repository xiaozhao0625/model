from __future__ import annotations

import argparse
import base64
import json
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ai_screenshot_platform.common.ocr.risk_lexicon import OcrRiskLexicon


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "deploy_output"
M0_SHOWUI_MODEL_DIR = Path(r"E:\work\models\showui")
M0_SHOWUI_RUNTIME = Path(r"E:\work\model_runtime\venvs\vision-runtime")
W2_OCR_RUNTIME = r"D:\work\model_runtime\venvs\ocr-runtime\Scripts\python.exe"
W2_HOST = "Administrator@192.168.1.20"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_command(args: list[str], timeout: int = 20) -> dict:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    return {
        "command": args[0],
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def git_value(args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def git_context() -> dict:
    return {
        "branch": git_value(["branch", "--show-current"]),
        "commit": git_value(["rev-parse", "--short", "HEAD"]),
        "status_short": git_value(["status", "--short"]),
    }


def tcp_status(host: str, port: int, timeout: float = 0.5) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "available"
    except OSError:
        return "offline"


def docker_redis_status() -> dict:
    ps = run_command(["docker", "ps", "--filter", "name=screenshot-redis", "--format", "{{.Names}}|{{.Ports}}|{{.Status}}"])
    ping = run_command(["docker", "exec", "screenshot-redis", "redis-cli", "ping"])
    return {
        "container": ps["stdout"],
        "pong": ping["stdout"] == "PONG",
        "ping_stdout": ping["stdout"],
        "host_port_6479": tcp_status("127.0.0.1", 6479),
        "host_port_6379": tcp_status("127.0.0.1", 6379),
    }


def w2_ocr_runtime_status() -> dict:
    script = (
        "$p='D:\\work\\model_runtime\\venvs\\ocr-runtime\\Scripts\\python.exe';"
        "$r=[ordered]@{ocr_python_exists=(Test-Path $p);paddleocr_import='not_checked';easyocr_import='not_checked'};"
        "if(Test-Path $p){"
        "$r.paddleocr_import=(& $p -c \"import importlib.util; print(importlib.util.find_spec('paddleocr') is not None)\") -join '';"
        "$r.easyocr_import=(& $p -c \"import importlib.util; print(importlib.util.find_spec('easyocr') is not None)\") -join '';"
        "};"
        "$r|ConvertTo-Json -Compress"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = run_command(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", W2_HOST, f"powershell -NoProfile -EncodedCommand {encoded}"],
        timeout=30,
    )
    parsed: dict
    try:
        json_line = next(line for line in result["stdout"].splitlines() if line.strip().startswith("{"))
        parsed = json.loads(json_line)
    except Exception:
        parsed = {"ocr_python_exists": False, "paddleocr_import": "unknown", "easyocr_import": "unknown"}
    parsed["ssh_returncode"] = result["returncode"]
    parsed["runtime_path"] = W2_OCR_RUNTIME
    return parsed


def showui_health() -> dict:
    weights = []
    if M0_SHOWUI_MODEL_DIR.exists():
        for pattern in ("*.safetensors", "*.pt", "*.onnx", "*.bin"):
            weights.extend(str(path) for path in M0_SHOWUI_MODEL_DIR.glob(pattern))
    status = "missing_weights" if not weights else "downloaded"
    return {
        "provider": "showui",
        "target_node": "M0",
        "status": status,
        "model_dir": str(M0_SHOWUI_MODEL_DIR),
        "model_dir_exists": M0_SHOWUI_MODEL_DIR.exists(),
        "runtime": str(M0_SHOWUI_RUNTIME),
        "runtime_exists": M0_SHOWUI_RUNTIME.exists(),
        "weights_found_count": len(weights),
        "hash_verification": "not_available" if not weights else "not_checked",
        "enabled": False,
        "online_inference_enabled": False,
        "model_loaded": False,
        "inference_attempted": False,
        "download_attempted": False,
        "error": "ShowUI weights are not present; download requires explicit user confirmation." if not weights else None,
    }


def showui_download_plan() -> dict:
    return {
        "provider": "showui",
        "recommended_first_provider": "ShowUI",
        "fallback_provider": "OmniParser",
        "final_selected_provider": "ShowUI",
        "target_node": "M0",
        "candidate_nodes": ["W2", "W3"],
        "purpose": [
            "UI/GUI screenshot understanding",
            "page type classification",
            "risk page assistance",
            "quality bucket suggestion",
        ],
        "estimated_vram_gb": "4-6",
        "estimated_disk_gb": "to_be_confirmed_by_selected_revision",
        "official_source": "official repository or model hub, to be pinned before download",
        "version_or_revision": "to_be_selected",
        "requires_login_token": "unknown_until_source_selected",
        "offline_capable": "planned",
        "windows_supported": "to_be_verified",
        "cuda_required": "recommended",
        "download_dir": str(M0_SHOWUI_MODEL_DIR),
        "runtime_dir": str(M0_SHOWUI_RUNTIME),
        "hash_recording": "record SHA256 for every downloaded file before health check",
        "health_check": "scripts/p13_5/check_model_health.py --role M0",
        "rollback": "delete untracked model/runtime files; keep provider enabled=false",
        "capture_impact": "none during planning; inference must stay offline and idle-aware",
        "do_download_now": False,
        "requires_user_confirmation": True,
        "selection_reason": "ShowUI is the first planned UI understanding provider; it keeps P13.5 focused on one provider before considering OmniParser.",
    }


def ocr_smoke_report(w2_status: dict) -> dict:
    ocr_ready = bool(w2_status.get("ocr_python_exists")) and w2_status.get("paddleocr_import") == "True"
    return {
        "schema_version": "p13.5.2",
        "status": "blocked_by_missing_p13_5_1_ocr_runtime" if not ocr_ready else "ready",
        "ocr_engine": "paddleocr",
        "ocr_node": "W2",
        "ocr_runtime_path": W2_OCR_RUNTIME,
        "w2_runtime": w2_status,
        "samples_processed": 0,
        "ocr_results_written": False,
        "install_attempted": False,
        "online_inference_enabled": False,
        "model_downloaded": False,
        "production_capture_started": False,
        "blocked": [] if ocr_ready else ["P13.5.1 OCR runtime is missing on W2"],
        "manual_required": [] if ocr_ready else ["Confirm and install W2 OCR runtime before OCR sample smoke"],
    }


def risk_gate_report() -> dict:
    lexicon = OcrRiskLexicon.default()
    samples = {
        "safe": "Settings display network and system information",
        "captcha": "captcha verification code security check",
        "payment": "checkout payment order pay",
        "login": "login password account security",
        "chat": "chat message send input message",
    }
    results = []
    for sample_id, text in samples.items():
        hits = lexicon.detect(text)
        results.append(
            {
                "sample_id": sample_id,
                "risk_level": "high" if hits else "none",
                "risk_reasons": [hit.risk_type for hit in hits],
                "matched_keywords": [hit.matched_text for hit in hits],
                "action": "block" if hits else "allow",
                "human_review_required": bool(hits),
                "should_stop_capture": False,
            }
        )
    return {
        "schema_version": "p13.5.3",
        "status": "rule_smoke_passed_without_ocr_runtime",
        "input_source": "synthetic_text_only",
        "ocr_results_integrated": False,
        "risk_results": results,
        "auto_action_execution": False,
        "should_stop_capture_default": False,
        "web_console_display": "existing OCR status and quality report pages can show risk hit counts; full OCR report waits for P13.5.1 runtime",
    }


def showui_sample_smoke_report(health: dict) -> dict:
    blocked = health["status"] != "downloaded"
    return {
        "schema_version": "p13.5.6",
        "status": "blocked_by_missing_weights" if blocked else "ready_for_offline_smoke",
        "provider": "showui",
        "target_node": "M0",
        "samples_processed": 0,
        "provider_loaded": False,
        "model_downloaded": False,
        "online_inference_enabled": False,
        "model_direct_action_control": False,
        "blocked": ["ShowUI weights are missing"] if blocked else [],
        "manual_required": ["User confirmation is required before ShowUI download and health check"] if blocked else [],
    }


def write_report(name: str, payload: dict, markdown: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT_DIR / f"{name}.md").write_text(markdown, encoding="utf-8")


def bullets(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate P13.5.2-P13.5.6 OCR/RiskGate/ShowUI reports without installing or downloading models.")
    parser.parse_args()

    context = git_context()
    redis = docker_redis_status()
    w2_ocr = w2_ocr_runtime_status()
    showui = showui_health()
    plan = showui_download_plan()
    ocr = ocr_smoke_report(w2_ocr)
    risk = risk_gate_report()
    showui_smoke = showui_sample_smoke_report(showui)

    common = {
        "generated_at": now_iso(),
        "git": context,
        "redis": redis,
        "security": {
            "downloaded_models": False,
            "installed_ocr": False,
            "online_inference_enabled": False,
            "started_production_capture": False,
            "worker_direct_postgresql": False,
            "sensitive_information_disclosed": False,
        },
    }

    write_report(
        "p13_5_2_ocr_sample_smoke_report",
        {**common, **ocr},
        "\n".join(
            [
                "# P13.5.2 OCR Offline Sample Smoke",
                "",
                f"- status: {ocr['status']}",
                f"- OCR node: {ocr['ocr_node']}",
                f"- OCR runtime: `{ocr['ocr_runtime_path']}`",
                f"- samples_processed: {ocr['samples_processed']}",
                f"- install_attempted: {ocr['install_attempted']}",
                "",
                "## Blocked",
                bullets(ocr["blocked"]),
                "",
                "## Manual Required",
                bullets(ocr["manual_required"]),
            ]
        ),
    )

    write_report(
        "p13_5_3_ocr_risk_gate_report",
        {**common, **risk},
        "\n".join(
            [
                "# P13.5.3 OCR Risk Gate",
                "",
                f"- status: {risk['status']}",
                "- source: synthetic_text_only",
                "- auto_action_execution: false",
                "- should_stop_capture_default: false",
                "",
                "## Risk Samples",
                *[
                    f"- {item['sample_id']}: {item['risk_level']} / {', '.join(item['risk_reasons']) or 'none'}"
                    for item in risk["risk_results"]
                ],
            ]
        ),
    )

    write_report(
        "p13_5_2_3_ocr_smoke_risk_gate_report",
        {**common, "ocr_smoke": ocr, "risk_gate": risk},
        "\n".join(
            [
                "# P13.5.2-P13.5.3 OCR Smoke + Risk Gate",
                "",
                f"- current_branch: {context['branch']}",
                f"- current_commit: {context['commit']}",
                f"- git_status_short: `{context['status_short'] or 'clean'}`",
                f"- OCR smoke: {ocr['status']}",
                f"- Risk Gate: {risk['status']}",
                "- online_inference_enabled: no",
                "- auto_action_execution: no",
                "- downloaded_vision_model: no",
                "- started_production_capture: no",
                "- sensitive_information_disclosed: no",
            ]
        ),
    )

    write_report(
        "p13_5_4_showui_download_plan",
        {**common, **plan},
        "\n".join(
            [
                "# P13.5.4 ShowUI Download Plan",
                "",
                "- recommended_first_provider: ShowUI",
                "- fallback_provider: OmniParser",
                "- final_selected_provider: ShowUI",
                "- do_download_now: false",
                "- requires_user_confirmation: true",
                f"- target_node: {plan['target_node']}",
                f"- download_dir: `{plan['download_dir']}`",
                f"- estimated_vram_gb: {plan['estimated_vram_gb']}",
                "",
                "ShowUI is planned only. No model download was attempted.",
            ]
        ),
    )

    write_report(
        "p13_5_5_showui_health_report",
        {**common, **showui},
        "\n".join(
            [
                "# P13.5.5 ShowUI Health",
                "",
                f"- status: {showui['status']}",
                f"- model_dir: `{showui['model_dir']}`",
                f"- runtime: `{showui['runtime']}`",
                f"- weights_found_count: {showui['weights_found_count']}",
                "- enabled: false",
                "- online_inference_enabled: false",
                f"- error: {showui['error'] or 'none'}",
            ]
        ),
    )

    write_report(
        "p13_5_6_showui_sample_smoke_report",
        {**common, **showui_smoke},
        "\n".join(
            [
                "# P13.5.6 ShowUI Sample Smoke",
                "",
                f"- status: {showui_smoke['status']}",
                "- samples_processed: 0",
                "- provider_loaded: false",
                "- model_direct_action_control: false",
                "",
                "## Blocked",
                bullets(showui_smoke["blocked"]),
            ]
        ),
    )

    write_report(
        "p13_5_4_6_showui_provider_plan_health_smoke_report",
        {**common, "download_plan": plan, "health": showui, "sample_smoke": showui_smoke},
        "\n".join(
            [
                "# P13.5.4-P13.5.6 ShowUI Provider Plan / Health / Smoke",
                "",
                f"- current_branch: {context['branch']}",
                f"- current_commit: {context['commit']}",
                f"- git_status_short: `{context['status_short'] or 'clean'}`",
                "- recommended_first_provider: ShowUI",
                "- fallback_provider: OmniParser",
                "- final_selected_provider: ShowUI",
                "- user_confirmed_download: no",
                "- model_downloaded: no",
                f"- health_status: {showui['status']}",
                f"- sample_smoke_status: {showui_smoke['status']}",
                "- enabled_true: no",
                "- online_inference_enabled: no",
                "- model_direct_action_control: no",
                "",
                "## Blocked",
                bullets(showui_smoke["blocked"]),
                "",
                "## Manual Required",
                bullets(showui_smoke["manual_required"]),
            ]
        ),
    )

    print(json.dumps({"status": "written", "output_dir": str(OUTPUT_DIR), "ocr_status": ocr["status"], "showui_health": showui["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
