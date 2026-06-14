from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request


WORKER_METHODS = {
    "worker_pc_game_w1": "ffmpeg_testsrc",
    "worker_pc_app_web_w2": "playwright_edge_local_html",
    "worker_android_w3": "adb_emulator_screencap",
}


def main() -> None:
    args = parse_args()
    client = MasterClient(args.master_url)
    client.post(f"/api/workers/{args.worker_id}/heartbeat", {})
    claim = client.post(f"/api/workers/{args.worker_id}/claim", {})
    if claim.get("status") != "claimed" or not claim.get("task"):
        print(json.dumps({"worker_id": args.worker_id, "claim_status": claim.get("status"), "task": None}, indent=2))
        return

    task = claim["task"]
    method = WORKER_METHODS.get(args.worker_id)
    if not method:
        raise ValueError(f"unsupported P14 worker_id: {args.worker_id}")

    result = execute_task(args, task, method)
    payload = {
        "app_id": str(task["app_id"]),
        "run_id": str(task["run_id"]),
        "status": result["status"],
        "valid_total": result["valid_total"],
        "fixed_count": result["fixed_count"],
        "low_count": result["low_count"],
        "high_count": result["high_count"],
        "rejected_count": result["rejected_count"],
        "run_dir": result["run_dir"],
        "summary_path": result["summary_path"],
        "error": result.get("error"),
    }
    report = client.post(f"/api/workers/{args.worker_id}/runs/{task['run_id']}/report", payload)
    result["claim_status"] = claim["status"]
    result["report_status"] = report["run"]["status"]
    result["master_run"] = report["run"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one P14 minimal real worker task.")
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--master-url", default="http://192.168.1.18:8000")
    parser.add_argument("--output-root", default=r"D:\work\runs")
    parser.add_argument("--target-total", type=int, default=3)
    parser.add_argument("--ffmpeg-path", default=r"D:\work\tools\ffmpeg\bin\ffmpeg.exe")
    parser.add_argument("--edge-path", default=r"C:\Program Files (x86)\Microsoft\EdgeCore\149.0.4022.69\msedge.exe")
    parser.add_argument("--adb-path", default=r"D:\work\tools\platform-tools\adb.exe")
    return parser.parse_args()


def execute_task(args: argparse.Namespace, task: dict[str, Any], method: str) -> dict[str, Any]:
    run_id = str(task["run_id"])
    worker_id = args.worker_id
    run_dir = Path(args.output_root) / run_id
    low_dir = run_dir / "low"
    for folder in [run_dir / "fixed", low_dir, run_dir / "high", run_dir / "rejected"]:
        folder.mkdir(parents=True, exist_ok=True)

    started_at = now_iso()
    if method == "ffmpeg_testsrc":
        files = capture_ffmpeg_testsrc(Path(args.ffmpeg_path), low_dir, args.target_total)
        platform = "pc_obs"
    elif method == "playwright_edge_local_html":
        files = capture_playwright_local_html(Path(args.edge_path), low_dir, run_dir, args.target_total)
        platform = "web"
    elif method == "adb_emulator_screencap":
        files = capture_adb_emulator(Path(args.adb_path), low_dir, args.target_total)
        platform = "android"
    else:
        raise ValueError(f"unsupported method: {method}")

    records, counts = build_records(
        files=files,
        run_id=run_id,
        worker_id=worker_id,
        task_id=run_id,
        platform=platform,
        capture_method=method,
    )
    finished_at = now_iso()
    meta_path = run_dir / "meta.jsonl"
    with meta_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = {
        "run_id": run_id,
        "task_id": run_id,
        "worker_id": worker_id,
        "status": "capture_completed",
        "valid_total": counts["valid_total"],
        "fixed_count": 0,
        "low_count": counts["low_count"],
        "high_count": 0,
        "rejected_count": counts["rejected_count"],
        "duplicate_count": counts["duplicate_count"],
        "target_total": args.target_total,
        "started_at": started_at,
        "finished_at": finished_at,
        "artifacts_root": str(run_dir),
        "meta_path": str(meta_path),
        "capture_method": method,
    }
    if method == "playwright_edge_local_html":
        summary.update({"content_only": True, "downloaded_browser": False, "ran_playwright_install": False, "real_web_capture": False})
    if method == "adb_emulator_screencap":
        summary.update({"apk_installed": False, "game_started": False, "real_app_capture": False})

    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "run.log").write_text(
        json.dumps({"event": "capture_completed", "run_id": run_id, "worker_id": worker_id, "count": len(files)}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "worker_id": worker_id,
        "run_id": run_id,
        "status": "capture_completed",
        "valid_total": counts["valid_total"],
        "fixed_count": 0,
        "low_count": counts["low_count"],
        "high_count": 0,
        "rejected_count": counts["rejected_count"],
        "duplicate_count": counts["duplicate_count"],
        "screenshot_count": len(files),
        "run_dir": str(run_dir),
        "meta_path": str(meta_path),
        "summary_path": str(summary_path),
        "capture_method": method,
    }


def capture_ffmpeg_testsrc(ffmpeg: Path, low_dir: Path, total: int) -> list[Path]:
    if not ffmpeg.exists():
        raise FileNotFoundError(str(ffmpeg))
    output_pattern = low_dir / "ffmpeg_testsrc_%03d.png"
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=duration={total}:size=1280x720:rate=1",
        "-frames:v",
        str(total),
        str(output_pattern),
    ]
    subprocess.run(command, check=True)
    return sorted(low_dir.glob("ffmpeg_testsrc_*.png"))


def capture_playwright_local_html(edge: Path, low_dir: Path, run_dir: Path, total: int) -> list[Path]:
    if not edge.exists():
        raise FileNotFoundError(str(edge))
    from playwright.sync_api import sync_playwright

    html_path = run_dir / "p14_local_content.html"
    html_path.write_text(
        """<!doctype html><html><head><meta charset='utf-8'><style>
body{margin:0;background:#101827;color:#e5e7eb;font-family:Arial,sans-serif}
#capture{width:900px;height:520px;display:flex;align-items:center;justify-content:center;flex-direction:column}
.frame{font-size:44px;font-weight:700}.sub{margin-top:16px;color:#93c5fd}
</style></head><body><main id='capture'><div class='frame' id='frame'></div><div class='sub'>local HTML only, no web login, no external network</div></main></body></html>""",
        encoding="utf-8",
    )
    files: list[Path] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(edge),
            headless=True,
            args=["--disable-gpu", "--no-first-run"],
        )
        page = browser.new_page(viewport={"width": 900, "height": 520}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="domcontentloaded")
        capture = page.locator("#capture")
        for index in range(1, total + 1):
            page.locator("#frame").evaluate("(node, value) => { node.textContent = value; }", f"P14-1 Frame {index}")
            output = low_dir / f"playwright_local_{index:03d}.png"
            capture.screenshot(path=str(output))
            files.append(output)
        browser.close()
    return files


def capture_adb_emulator(adb: Path, low_dir: Path, total: int) -> list[Path]:
    if not adb.exists():
        raise FileNotFoundError(str(adb))
    devices = subprocess.check_output([str(adb), "devices"], text=True, encoding="utf-8", errors="ignore")
    if "emulator-" not in devices:
        raise RuntimeError("no emulator device visible in adb devices")
    boot_completed = subprocess.check_output([str(adb), "shell", "getprop", "sys.boot_completed"], text=True, encoding="utf-8", errors="ignore").strip()
    if boot_completed != "1":
        raise RuntimeError(f"emulator boot not completed: {boot_completed}")
    files: list[Path] = []
    for index in range(1, total + 1):
        output = low_dir / f"adb_emulator_{index:03d}.png"
        with output.open("wb") as handle:
            subprocess.run([str(adb), "exec-out", "screencap", "-p"], check=True, stdout=handle)
        files.append(output)
        time.sleep(1)
    return files


def build_records(
    files: list[Path],
    run_id: str,
    worker_id: str,
    task_id: str,
    platform: str,
    capture_method: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    duplicate_count = 0
    rejected_count = 0
    valid_total = 0
    for file_path in files:
        digest = sha256(file_path)
        is_duplicate = digest in seen
        seen.add(digest)
        if is_duplicate:
            duplicate_count += 1
        else:
            valid_total += 1
        width, height = png_dimensions(file_path)
        records.append(
            {
                "run_id": run_id,
                "worker_id": worker_id,
                "task_id": task_id,
                "platform": platform,
                "bucket": "low",
                "file_path": str(file_path),
                "content_hash": digest,
                "created_at": now_iso(),
                "capture_method": capture_method,
                "width": width,
                "height": height,
                "is_duplicate": is_duplicate,
                "rejected_reason": "duplicate" if is_duplicate else None,
            }
        )
    return records, {
        "valid_total": valid_total,
        "low_count": valid_total,
        "rejected_count": rejected_count,
        "duplicate_count": duplicate_count,
    }


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    return 0, 0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MasterClient:
    def __init__(self, master_url: str) -> None:
        self.master_url = master_url.rstrip("/")

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.master_url + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("code") != 0:
            raise ValueError(data)
        return data["data"]


if __name__ == "__main__":
    main()
