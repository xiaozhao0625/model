from __future__ import annotations

import base64
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Any


RUN_ROOT = PureWindowsPath(r"D:\work\runs")
ALLOWED_BUCKETS = {"fixed", "low", "high", "rejected", "duplicates"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".json", ".jsonl", ".txt", ".log"}
KNOWN_RUN_WORKERS = {
    "p14_w1_ffmpeg_testsrc_20260615_001142": "worker_pc_game_w1",
    "p14_w2_playwright_local_20260615_001142": "worker_pc_app_web_w2",
    "p14_w3_adb_emulator_20260615_001142": "worker_android_w3",
}
WORKERS = {
    "worker_pc_game_w1": {
        "role": "W1 PC Game Worker",
        "host": "192.168.1.34",
        "ssh_user": "Administrator",
    },
    "worker_pc_app_web_w2": {
        "role": "W2 PC App / Web Worker",
        "host": "192.168.1.20",
        "ssh_user": "Administrator",
    },
    "worker_android_w3": {
        "role": "W3 Android Worker",
        "host": "192.168.1.21",
        "ssh_user": "Administrator",
    },
}


@dataclass(frozen=True)
class RunLocation:
    run_id: str
    worker_id: str
    worker_role: str
    worker_host: str
    ssh_user: str
    artifact_root: str


class ArtifactInspectorService:
    def __init__(self, run_repo: Any | None = None) -> None:
        self.run_repo = run_repo

    def describe(self, run_id: str) -> dict[str, Any]:
        location = self._resolve_run_location(run_id)
        payload = self._read_remote_artifacts(location)
        summary = payload.get("summary") or {}
        meta = payload.get("meta") or []
        bucket_counts = self._bucket_counts(summary, meta)
        return {
            "run_id": run_id,
            "task_id": summary.get("task_id", run_id),
            "worker_id": location.worker_id,
            "worker_role": location.worker_role,
            "worker_host": location.worker_host,
            "artifact_root": location.artifact_root,
            "status": summary.get("status", "unknown"),
            "summary": summary,
            "bucket_counts": bucket_counts,
            "sample_files": self._samples_from_meta(meta, limit=20),
            "has_meta_jsonl": bool(payload.get("has_meta_jsonl")),
            "has_summary_json": bool(payload.get("has_summary_json")),
            "can_open_folder": True,
            "can_download_sample": True,
        }

    def samples(self, run_id: str, bucket: str = "low", limit: int = 20) -> list[dict[str, Any]]:
        if bucket not in ALLOWED_BUCKETS:
            raise ValueError("unsupported artifact bucket")
        location = self._resolve_run_location(run_id)
        payload = self._read_remote_artifacts(location)
        meta = payload.get("meta") or []
        selected = self._samples_from_meta(meta, bucket=bucket, limit=max(1, min(limit, 20)))
        return selected

    def thumbnail(self, run_id: str, file_id: str) -> tuple[bytes, str]:
        location = self._resolve_run_location(run_id)
        relative_path = self._validate_file_id(file_id)
        extension = relative_path.suffix.lower()
        if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("unsupported thumbnail type")
        remote_path = RUN_ROOT / run_id / relative_path
        payload = self._run_remote_json(
            location,
            rf"""
$path = "{remote_path}"
if (!(Test-Path -LiteralPath $path -PathType Leaf)) {{
  @{{ status = "path_missing" }} | ConvertTo-Json -Compress
  exit 0
}}
@{{ status = "ok"; content_base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) }} | ConvertTo-Json -Compress
""",
        )
        if payload.get("status") != "ok":
            raise FileNotFoundError(file_id)
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(extension, "image/png")
        return base64.b64decode(str(payload["content_base64"])), content_type

    def open_folder(self, run_id: str, bucket: str | None = None, file_id: str | None = None) -> dict[str, Any]:
        location = self._resolve_run_location(run_id)
        if bucket is not None and bucket not in ALLOWED_BUCKETS - {"duplicates"}:
            raise ValueError("unsupported artifact bucket")
        relative_path = self._validate_file_id(file_id) if file_id else None
        target = RUN_ROOT / run_id
        if bucket:
            target = target / bucket
        if relative_path:
            target = RUN_ROOT / run_id / relative_path
        payload = self._run_remote_json(
            location,
            rf"""
$path = "{target}"
if (!(Test-Path -LiteralPath $path)) {{
  @{{ status = "path_missing"; desktop_session_required = $false }} | ConvertTo-Json -Compress
  exit 0
}}
try {{
  if ((Get-Item -LiteralPath $path).PSIsContainer) {{
    Start-Process explorer.exe -ArgumentList @($path)
  }} else {{
    Start-Process explorer.exe -ArgumentList @("/select,",$path)
  }}
  @{{ status = "opened"; desktop_session_required = $false }} | ConvertTo-Json -Compress
}} catch {{
  @{{ status = "desktop_session_required"; desktop_session_required = $true }} | ConvertTo-Json -Compress
}}
""",
        )
        return {
            "run_id": run_id,
            "worker_id": location.worker_id,
            "status": payload.get("status", "failed"),
            "desktop_session_required": bool(payload.get("desktop_session_required", False)),
        }

    def package_sample(self, run_id: str, buckets: list[str] | None = None, limit_per_bucket: int = 20) -> dict[str, Any]:
        location = self._resolve_run_location(run_id)
        selected_buckets = buckets or ["fixed", "low", "high", "rejected"]
        for bucket in selected_buckets:
            if bucket not in ALLOWED_BUCKETS - {"duplicates"}:
                raise ValueError("unsupported artifact bucket")
        limit = max(1, min(limit_per_bucket, 20))
        bucket_literal = "@(" + ",".join(f'"{bucket}"' for bucket in selected_buckets) + ")"
        payload = self._run_remote_json(
            location,
            rf"""
$runRoot = "{RUN_ROOT / run_id}"
if (!(Test-Path -LiteralPath $runRoot -PathType Container)) {{
  @{{ status = "path_missing" }} | ConvertTo-Json -Compress
  exit 0
}}
$inspection = Join-Path $runRoot "_inspection"
New-Item -ItemType Directory -Force -Path $inspection | Out-Null
$zip = Join-Path $inspection "sample_inspection.zip"
if (Test-Path -LiteralPath $zip) {{ Remove-Item -LiteralPath $zip -Force }}
$files = New-Object System.Collections.Generic.List[string]
foreach ($bucket in {bucket_literal}) {{
  $dir = Join-Path $runRoot $bucket
  if (Test-Path -LiteralPath $dir -PathType Container) {{
    Get-ChildItem -LiteralPath $dir -File |
      Where-Object {{ @(".png",".jpg",".jpeg",".webp",".json",".jsonl",".txt",".log") -contains $_.Extension.ToLowerInvariant() }} |
      Select-Object -First {limit} |
      ForEach-Object {{ $files.Add($_.FullName) }}
  }}
}}
foreach ($name in @("summary.json","meta.jsonl","run.log")) {{
  $path = Join-Path $runRoot $name
  if (Test-Path -LiteralPath $path -PathType Leaf) {{ $files.Add($path) }}
}}
if ($files.Count -eq 0) {{
  @{{ status = "empty"; zip_path = $null; file_count = 0 }} | ConvertTo-Json -Compress
  exit 0
}}
Compress-Archive -LiteralPath $files.ToArray() -DestinationPath $zip -Force
@{{ status = "packaged"; zip_path = $zip; file_count = $files.Count; download_id = "{run_id}:sample" }} | ConvertTo-Json -Compress
""",
        )
        return {
            "run_id": run_id,
            "worker_id": location.worker_id,
            "status": payload.get("status", "failed"),
            "zip_path": payload.get("zip_path"),
            "file_count": payload.get("file_count", 0),
            "download_id": payload.get("download_id"),
        }

    def download_sample(self, run_id: str) -> tuple[bytes, str]:
        location = self._resolve_run_location(run_id)
        zip_path = RUN_ROOT / run_id / "_inspection" / "sample_inspection.zip"
        payload = self._run_remote_json(
            location,
            rf"""
$path = "{zip_path}"
if (!(Test-Path -LiteralPath $path -PathType Leaf)) {{
  @{{ status = "path_missing" }} | ConvertTo-Json -Compress
  exit 0
}}
@{{ status = "ok"; content_base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)); file_name = "sample_inspection.zip" }} | ConvertTo-Json -Compress
""",
        )
        if payload.get("status") != "ok":
            raise FileNotFoundError("sample zip is not available")
        return base64.b64decode(str(payload["content_base64"])), str(payload.get("file_name", "sample_inspection.zip"))

    def _read_remote_artifacts(self, location: RunLocation) -> dict[str, Any]:
        return self._run_remote_json(
            location,
            rf"""
$runRoot = "{location.artifact_root}"
$summaryPath = Join-Path $runRoot "summary.json"
$metaPath = Join-Path $runRoot "meta.jsonl"
if (!(Test-Path -LiteralPath $runRoot -PathType Container)) {{
  @{{ status = "path_missing"; summary = $null; meta = @(); has_summary_json = $false; has_meta_jsonl = $false }} | ConvertTo-Json -Depth 8 -Compress
  exit 0
}}
$summary = $null
if (Test-Path -LiteralPath $summaryPath -PathType Leaf) {{
  $summary = Get-Content -LiteralPath $summaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
}}
$meta = @()
if (Test-Path -LiteralPath $metaPath -PathType Leaf) {{
  $meta = Get-Content -LiteralPath $metaPath -Encoding UTF8 | Where-Object {{ $_.Trim() }} | ForEach-Object {{ $_ | ConvertFrom-Json }}
}}
@{{
  status = "ok"
  summary = $summary
  meta = @($meta)
  has_summary_json = [bool](Test-Path -LiteralPath $summaryPath -PathType Leaf)
  has_meta_jsonl = [bool](Test-Path -LiteralPath $metaPath -PathType Leaf)
}} | ConvertTo-Json -Depth 12 -Compress
""",
        )

    def _resolve_run_location(self, run_id: str) -> RunLocation:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", run_id):
            raise ValueError("invalid run_id")
        worker_id = self._worker_for_run(run_id)
        if worker_id not in WORKERS:
            raise ValueError("unknown run worker")
        worker = WORKERS[worker_id]
        return RunLocation(
            run_id=run_id,
            worker_id=worker_id,
            worker_role=str(worker["role"]),
            worker_host=str(worker["host"]),
            ssh_user=str(worker["ssh_user"]),
            artifact_root=str(RUN_ROOT / run_id),
        )

    def _worker_for_run(self, run_id: str) -> str:
        if self.run_repo is not None:
            try:
                record = self.run_repo.get(run_id)
                if record is not None and record.worker_id:
                    return record.worker_id
            except Exception:
                pass
        if run_id in KNOWN_RUN_WORKERS:
            return KNOWN_RUN_WORKERS[run_id]
        if "_w1_" in run_id or run_id.startswith("p14_w1_"):
            return "worker_pc_game_w1"
        if "_w2_" in run_id or run_id.startswith("p14_w2_"):
            return "worker_pc_app_web_w2"
        if "_w3_" in run_id or run_id.startswith("p14_w3_"):
            return "worker_android_w3"
        raise ValueError("unknown run worker")

    def _run_remote_json(self, location: RunLocation, script: str) -> dict[str, Any]:
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        target = f"{location.ssh_user}@{location.worker_host}"
        result: subprocess.CompletedProcess[str] | None = None
        for attempt in range(2):
            result = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=8",
                    target,
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-EncodedCommand",
                    encoded,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                break
            if attempt == 0:
                time.sleep(0.5)
        if result is None:
            raise RuntimeError("worker action did not run")
        if result.returncode != 0:
            raise RuntimeError(f"worker action failed: {result.stderr.strip() or result.stdout.strip()}")
        output = result.stdout.strip()
        if "\n" in output:
            output = output.splitlines()[-1]
        return json.loads(output)

    @staticmethod
    def _bucket_counts(summary: dict[str, Any], meta: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "fixed": int(summary.get("fixed_count", 0) or 0),
            "low": int(summary.get("low_count", 0) or sum(1 for item in meta if item.get("bucket") == "low" and not item.get("is_duplicate"))),
            "high": int(summary.get("high_count", 0) or 0),
            "rejected": int(summary.get("rejected_count", 0) or 0),
            "duplicates": int(summary.get("duplicate_count", 0) or sum(1 for item in meta if item.get("is_duplicate"))),
        }

    def _samples_from_meta(self, meta: list[dict[str, Any]], bucket: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        for item in meta:
            item_bucket = str(item.get("bucket", "low"))
            is_duplicate = bool(item.get("is_duplicate", False))
            display_bucket = "duplicates" if is_duplicate else item_bucket
            if bucket is not None and display_bucket != bucket:
                continue
            path = PureWindowsPath(str(item.get("file_path", "")))
            file_id = f"{item_bucket}/{path.name}"
            if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            samples.append(
                {
                    "file_id": file_id,
                    "file_name": path.name,
                    "bucket": display_bucket,
                    "width": int(item.get("width", 0) or 0),
                    "height": int(item.get("height", 0) or 0),
                    "is_duplicate": is_duplicate,
                    "rejected_reason": item.get("rejected_reason"),
                    "thumbnail_url": "",
                    "safe_display_path": f"D:\\work\\runs\\<run_id>\\{file_id}",
                    "capture_method": item.get("capture_method", "unknown"),
                }
            )
            if len(samples) >= limit:
                break
        return samples

    @staticmethod
    def _validate_file_id(file_id: str | None) -> PureWindowsPath:
        if not file_id:
            raise ValueError("file_id is required")
        normalized = file_id.replace("/", "\\")
        if ".." in normalized or normalized.startswith("\\"):
            raise ValueError("invalid file_id")
        path = PureWindowsPath(normalized)
        parts = path.parts
        if len(parts) != 2 or parts[0] not in ALLOWED_BUCKETS - {"duplicates"}:
            raise ValueError("invalid file_id")
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError("unsupported file type")
        return path
