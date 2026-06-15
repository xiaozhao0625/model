from __future__ import annotations

import argparse
import json
from urllib.parse import quote
from urllib.request import Request, urlopen


def api_json(base_url: str, path: str) -> dict:
    with urlopen(Request(f"{base_url.rstrip('/')}{path}", headers={"Accept": "application/json"}), timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("code") != 0 and payload.get("ok") is not True:
        raise RuntimeError(f"API failed: {path}")
    return payload["data"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    artifact = api_json(args.base_url, f"/api/runs/{args.run_id}/artifacts")
    samples = artifact.get("sample_files") or []
    thumbnail_checks = []
    for sample in samples[:5]:
        file_id = sample["file_id"]
        path = f"/api/runs/{args.run_id}/artifacts/thumbnail?file_id={quote(file_id)}"
        try:
            with urlopen(Request(f"{args.base_url.rstrip()}{path}"), timeout=12) as response:
                thumbnail_checks.append({"file_id": file_id, "http_status": response.status, "bytes": len(response.read())})
        except Exception as exc:
            thumbnail_checks.append({"file_id": file_id, "http_status": 0, "error": str(exc)})
    failures = [item for item in thumbnail_checks if item.get("http_status") != 200 or int(item.get("bytes") or 0) <= 0]
    output = {
        "status": "passed" if not failures and samples else "failed",
        "run_id": args.run_id,
        "artifact_status": artifact.get("artifact_status"),
        "sample_count": len(samples),
        "thumbnail_url_count": sum(1 for sample in samples if sample.get("thumbnail_url")),
        "image_url_count": sum(1 for sample in samples if sample.get("image_url")),
        "thumbnail_checks": thumbnail_checks,
        "failures": failures,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
