from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], cwd: Path) -> tuple[int, dict]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    payload = parse_json(result.stdout)
    if payload is None:
        payload = {"stdout": result.stdout, "stderr": result.stderr}
    return result.returncode, payload


def parse_json(text: str) -> dict | None:
    decoder = json.JSONDecoder()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload, _ = decoder.raw_decode(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-root", default="runs/master/p14_5_gameonly_qa")
    parser.add_argument("--target-total", type=int, default=12)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    output_root = repo / args.output_root

    plan_code, plan = run_command(
        [
            args.python,
            "scripts/p14/p14_5_onegame_obs_mvp.py",
            "--mode",
            "plan",
            "--output-root",
            str(output_root),
            "--target-total",
            str(args.target_total),
        ],
        repo,
    )
    dry_code, dry = run_command(
        [
            args.python,
            "scripts/p14/p14_5_onegame_obs_mvp.py",
            "--mode",
            "dry-run",
            "--output-root",
            str(output_root),
            "--target-total",
            str(args.target_total),
            "--inject-quality-fixtures",
        ],
        repo,
    )

    failures: list[dict] = []
    if plan_code == 0 or plan.get("status") != "blocked":
        failures.append({"step": "plan", "reason": "plan_should_block_without_user_ready", "payload": plan})
    if dry_code != 0 or dry.get("status") != "capture_completed":
        failures.append({"step": "dry_run", "reason": "dry_run_failed", "payload": dry})
    run_dir = Path(str(dry.get("run_dir", "")))
    required = ["summary.json", "meta.jsonl", "quality_report.json", "run.log", "action_log.jsonl"]
    missing = [name for name in required if not (run_dir / name).is_file()]
    if missing:
        failures.append({"step": "artifacts", "reason": "missing_required_files", "missing": missing})
    if dry.get("test_source") is not True or dry.get("production_capture") is not False:
        failures.append({"step": "dry_run", "reason": "test_source_flags_incorrect", "payload": dry})
    if int(dry.get("duplicate_count") or 0) < 1 or int(dry.get("black_screen_count") or 0) < 1:
        failures.append({"step": "quality_gate", "reason": "fixtures_not_detected", "payload": dry})
    if dry.get("online_inference") is not False or dry.get("model_action_control") is not False:
        failures.append({"step": "safety", "reason": "unsafe_model_flags", "payload": dry})

    output = {
        "status": "passed" if not failures else "failed",
        "plan": plan,
        "dry_run": dry,
        "required_files": required,
        "failures": failures,
        "safety": {
            "downloaded_game": False,
            "logged_in": False,
            "captcha_handled": False,
            "matchmaking_or_ranked": False,
            "online_inference": False,
            "model_action_control": False,
            "automatic_upload": False,
            "automatic_cleanup": False,
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
