from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a P13 preflight report to Master API diagnostics ingest.")
    parser.add_argument("--report", required=True)
    parser.add_argument("--master-url", required=True)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    print(json.dumps(upload_report(Path(args.report), args.master_url, args.timeout), ensure_ascii=False, indent=2, sort_keys=True))


def upload_report(report_path: Path, master_url: str, timeout: float = 5.0) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    endpoint = master_url.rstrip("/") + "/api/diagnostics/ingest"
    payload = {
        "machine_name": report.get("machine_name"),
        "role": report.get("role"),
        "status": report.get("status", "unknown"),
        "report_type": "p13_preflight",
        "payload": report,
        "source_path": str(report_path),
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"upload_status": "ok", "http_status": response.status}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "upload_status": "failed",
            "reason": type(exc).__name__,
            "local_report_kept": True,
            "next_step": "M0 Master API 可用后重新运行上传命令。",
        }


if __name__ == "__main__":
    main()
