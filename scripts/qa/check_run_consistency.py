from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import PureWindowsPath
from urllib.request import Request, urlopen


WORKER_BY_MARKER = {
    "_w1_": ("worker_pc_game_w1", "Administrator@192.168.1.34"),
    "_w2_": ("worker_pc_app_web_w2", "Administrator@192.168.1.20"),
    "_w3_": ("worker_android_w3", "Administrator@192.168.1.21"),
}


def api_json(base_url: str, path: str) -> dict:
    with urlopen(Request(f"{base_url.rstrip('/')}{path}", headers={"Accept": "application/json"}), timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("code") != 0 and payload.get("ok") is not True:
        raise RuntimeError(f"API failed: {path}")
    return payload["data"]


def worker_target(run_id: str, worker_id: str | None) -> str:
    if worker_id == "worker_pc_game_w1" or "_w1_" in run_id:
        return "Administrator@192.168.1.34"
    if worker_id == "worker_pc_app_web_w2" or "_w2_" in run_id:
        return "Administrator@192.168.1.20"
    if worker_id == "worker_android_w3" or "_w3_" in run_id:
        return "Administrator@192.168.1.21"
    raise RuntimeError(f"unknown worker for {run_id}")


def remote_counts(run_id: str, target: str) -> dict:
    root = PureWindowsPath(r"D:\work\runs") / run_id
    script = rf"""
$root = "{root}"
$summary = Join-Path $root "summary.json"
$meta = Join-Path $root "meta.jsonl"
$buckets = @("fixed","low","high","rejected")
$result = [ordered]@{{
  summary_exists = Test-Path -LiteralPath $summary -PathType Leaf
  meta_exists = Test-Path -LiteralPath $meta -PathType Leaf
  meta_count = 0
  file_count = 0
  fixed_count_by_file = 0
  low_count_by_file = 0
  high_count_by_file = 0
  rejected_count_by_file = 0
}}
if ($result.meta_exists) {{ $result.meta_count = (Get-Content -LiteralPath $meta | Where-Object {{ $_.Trim() }} | Measure-Object).Count }}
foreach ($bucket in $buckets) {{
  $dir = Join-Path $root $bucket
  $count = 0
  if (Test-Path -LiteralPath $dir -PathType Container) {{
    $count = (Get-ChildItem -LiteralPath $dir -File -Include *.png,*.jpg,*.jpeg,*.webp | Measure-Object).Count
  }}
  $result["$($bucket)_count_by_file"] = $count
  $result.file_count += $count
}}
$result | ConvertTo-Json -Compress
"""
    encoded = subprocess.check_output(
        [sys.executable, "-c", "import base64,sys;print(base64.b64encode(sys.stdin.read().encode('utf-16le')).decode())"],
        input=script,
        text=True,
    ).strip()
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", target, "powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        return {"remote_error": completed.stderr.strip() or completed.stdout.strip()}
    for line in completed.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return {"remote_error": "no_json"}


def check_one(base_url: str, run_id: str) -> dict:
    run = api_json(base_url, f"/api/runs/{run_id}")
    artifacts = api_json(base_url, f"/api/runs/{run_id}/artifacts")
    summary = artifacts.get("summary") or {}
    samples = artifacts.get("sample_files") or []
    target = worker_target(run_id, run.get("worker_id"))
    files = remote_counts(run_id, target)
    api_artifact_count = len(samples)
    thumbnail_count = sum(1 for item in samples if item.get("thumbnail_url"))
    mismatch_reasons = []
    db_valid_total = int(run.get("valid_total") or 0)
    summary_valid_total = int(summary.get("valid_total") or 0)
    meta_count = int(files.get("meta_count") or 0)
    file_count = int(files.get("file_count") or 0)
    if db_valid_total and summary_valid_total and db_valid_total != summary_valid_total:
        mismatch_reasons.append("db_summary_mismatch")
    if summary_valid_total and meta_count and abs(summary_valid_total - meta_count) > int(summary.get("duplicate_count") or 0):
        mismatch_reasons.append("summary_meta_mismatch")
    if summary_valid_total and file_count and summary_valid_total > file_count:
        mismatch_reasons.append("summary_file_mismatch")
    if summary_valid_total and api_artifact_count == 0:
        mismatch_reasons.append("file_api_mismatch")
    if api_artifact_count and thumbnail_count != api_artifact_count:
        mismatch_reasons.append("api_thumbnail_mismatch")
    return {
        "run_id": run_id,
        "worker_id": run.get("worker_id"),
        "db_valid_total": db_valid_total,
        "summary_valid_total": summary_valid_total,
        "meta_count": meta_count,
        "file_count": file_count,
        "api_artifact_count": api_artifact_count,
        "thumbnail_count": thumbnail_count,
        "ocr_result_count": sum(1 for item in samples if item.get("ocr_status") == "available"),
        "showui_result_count": sum(1 for item in samples if item.get("showui_status") == "available"),
        "mismatch": bool(mismatch_reasons),
        "mismatch_reasons": mismatch_reasons,
        "remote": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--run-id", action="append")
    parser.add_argument("--batch")
    parser.add_argument("--recent", type=int, default=0)
    args = parser.parse_args()

    run_ids = args.run_id or []
    if args.batch or args.recent:
        query = []
        if args.batch:
            query.append(f"batch={args.batch}")
        query.append(f"limit={args.recent or 20}")
        query.append("sort=created_at_desc")
        listed = api_json(args.base_url, f"/api/runs?{'&'.join(query)}")
        run_ids.extend(item["run_id"] for item in listed.get("items", []))
    if not run_ids:
        raise SystemExit("--run-id, --batch, or --recent is required")

    results = [check_one(args.base_url, run_id) for run_id in dict.fromkeys(run_ids)]
    output = {"status": "passed" if not any(item["mismatch"] for item in results) else "failed", "results": results}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
