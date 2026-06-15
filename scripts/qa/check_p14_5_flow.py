from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def api_json(base_url: str, path: str, method: str = "GET", payload: dict | None = None, timeout: float = 8) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
    start = time.perf_counter()
    with urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
        if not (data.get("code") == 0 or data.get("ok") is True):
            raise RuntimeError(data.get("error") or data.get("message") or path)
        return {"latency_ms": int((time.perf_counter() - start) * 1000), "data": data["data"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--run-id", default="p14_4_batch3C_w3_safe_ui_03_20260615_190322_run")
    parser.add_argument("--timeout", type=float, default=8)
    args = parser.parse_args()

    failures: list[dict] = []
    results: list[dict] = []
    sample_tasks = {
        "dry_run": True,
        "tasks": [
            {
                "run_id": "p14_5_w1_safe_window_preview",
                "app_id": "p14_5_safe_window",
                "role": "W1",
                "capture_method": "windows_safe_window_capture",
                "target_total": 30,
            },
            {
                "run_id": "p14_5_w1_testsrc_preview",
                "app_id": "p14_5_forbidden_testsrc",
                "role": "W1",
                "capture_method": "ffmpeg_testsrc",
                "target_total": 30,
            },
        ],
    }
    checks = [
        ("dashboard", "GET", "/api/p14-5/operator-dashboard", None),
        ("batch_validate", "POST", "/api/p14-5/batch-tasks/validate", sample_tasks),
        ("manual_queue", "GET", "/api/p14-5/manual-required", None),
        ("claim_guard", "POST", "/api/p14-5/claim-guard", {"worker_id": "worker_pc_game_w1", "run_id": "p14_5_w2_web_content_preview"}),
        ("retry_plan", "POST", f"/api/p14-5/runs/{args.run_id}/retry-plan", {}),
        ("upload_preview", "POST", f"/api/p14-5/runs/{args.run_id}/upload-preview", {}),
        ("cleanup_preview", "POST", f"/api/p14-5/runs/{args.run_id}/cleanup-preview", {}),
        ("diagnostic_bundle", "POST", f"/api/p14-5/runs/{args.run_id}/diagnostic-bundle", {"include_samples": False}),
        ("disk_status", "GET", "/api/p14-5/disk-status", None),
        ("stuck_recovery", "POST", "/api/p14-5/recovery/stuck-tasks", {"dry_run": True}),
    ]

    for name, method, path, payload in checks:
        try:
            item = api_json(args.base_url, path, method=method, payload=payload, timeout=args.timeout)
            data = item["data"]
            results.append({"name": name, "path": path, "latency_ms": item["latency_ms"], "status": data.get("status", "ok")})
            if name == "batch_validate":
                if data.get("production_scale_capture") is not False or data.get("online_inference") is not False:
                    failures.append({"name": name, "reason": "unsafe_flags", "data": data})
                blocked = data.get("tasks", [])[1].get("blocked", [])
                if "test_source_not_allowed_for_production_flow" not in blocked:
                    failures.append({"name": name, "reason": "testsrc_not_blocked", "blocked": blocked})
            if name == "cleanup_preview" and data.get("delete_allowed") is not False:
                failures.append({"name": name, "reason": "protected_run_cleanup_not_blocked", "data": data})
            if name == "diagnostic_bundle":
                if data.get("screenshots_included") is not False or data.get("secrets_included") is not False:
                    failures.append({"name": name, "reason": "diagnostic_includes_forbidden_content", "data": data})
            if name == "stuck_recovery" and data.get("mutated") is not False:
                failures.append({"name": name, "reason": "stuck_recovery_mutated_state", "data": data})
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            failures.append({"name": name, "path": path, "reason": type(exc).__name__, "message": str(exc)})

    output = {
        "status": "passed" if not failures else "failed",
        "base_url": args.base_url,
        "run_id": args.run_id,
        "results": results,
        "failures": failures,
        "safety": {
            "production_scale_capture": False,
            "online_inference": False,
            "model_action_control": False,
            "automatic_upload": False,
            "unconfirmed_cleanup": False,
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
