from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch_json(base_url: str, path: str, timeout: float) -> dict:
    start = time.perf_counter()
    request = Request(f"{base_url.rstrip('/')}{path}", headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        latency_ms = int((time.perf_counter() - start) * 1000)
        payload = json.loads(body)
        return {
            "path": path,
            "http_status": response.status,
            "latency_ms": latency_ms,
            "envelope_ok": payload.get("code") == 0 or payload.get("ok") is True,
            "data_type": type(payload.get("data")).__name__,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--run-id", default="p14_4_batch3C_w3_safe_ui_03_20260615_190322_run")
    parser.add_argument("--timeout", type=float, default=8)
    args = parser.parse_args()

    paths = [
        "/health",
        "/api/workers",
        "/api/tasks?sort=created_at_desc&limit=20",
        "/api/runs?sort=created_at_desc&limit=20",
        "/api/runs?worker_id=worker_pc_game_w1&limit=5",
        "/api/runs?status=capture_completed&limit=5",
        f"/api/runs/{args.run_id}",
        f"/api/runs/{args.run_id}/artifacts",
        f"/api/runs/{args.run_id}/artifacts/summary",
        "/api/ocr/status",
        "/api/model/deployment-matrix",
    ]
    results = []
    failures = []
    for path in paths:
        try:
            result = fetch_json(args.base_url, path, args.timeout)
            if result["http_status"] != 200 or not result["envelope_ok"]:
                failures.append({"path": path, "reason": "bad_response", "result": result})
            if "/artifacts" in path and result["latency_ms"] > 3000:
                failures.append({"path": path, "reason": "artifact_listing_slow", "latency_ms": result["latency_ms"]})
            results.append(result)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures.append({"path": path, "reason": type(exc).__name__, "message": str(exc)})

    output = {"status": "passed" if not failures else "failed", "base_url": args.base_url, "results": results, "failures": failures}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
