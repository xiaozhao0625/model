from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Any


RUN_ROOT = PureWindowsPath(r"D:\work\runs")
SHOWUI_RESULTS_PATH = Path(r"E:\work\model_runtime\smoke_outputs\showui\showui_sample_results.jsonl")
W2_OCR_RESULTS_PATH = PureWindowsPath(r"D:\work\model_runtime\reports\ocr_sample_smoke\ocr_results.jsonl")
OCR_RESULTS_CACHE_PATH = Path("runs/master/analysis_cache/ocr_results.jsonl").resolve()
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


def location_for_worker(worker_id: str) -> RunLocation:
    worker = WORKERS[worker_id]
    return RunLocation(
        run_id="_analysis",
        worker_id=worker_id,
        worker_role=str(worker["role"]),
        worker_host=str(worker["host"]),
        ssh_user=str(worker["ssh_user"]),
        artifact_root=str(RUN_ROOT / "_analysis"),
    )


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
        self.cache_dir = Path("runs/master/artifact_listing_cache").resolve()
        self.cache_ttl_seconds = 600
        self._refreshing: set[str] = set()
        self._refresh_lock = threading.Lock()

    def describe(self, run_id: str) -> dict[str, Any]:
        location = self._resolve_run_location(run_id)
        payload = self._read_remote_artifacts(location)
        summary = payload.get("summary") or {}
        meta = payload.get("meta") or []
        bucket_counts = self._bucket_counts(summary, meta)
        analysis = self._analysis_lookup(location)
        return {
            "run_id": run_id,
            "task_id": summary.get("task_id", run_id),
            "worker_id": location.worker_id,
            "worker_role": location.worker_role,
            "worker_host": location.worker_host,
            "artifact_root": location.artifact_root,
            "status": summary.get("status", "unknown"),
            "artifact_status": payload.get("status", "unknown"),
            "cache_hit": bool(payload.get("cache_hit")),
            "summary": summary,
            "bucket_counts": bucket_counts,
            "sample_files": self._samples_from_meta(meta, location=location, analysis=analysis, limit=20),
            "has_meta_jsonl": bool(payload.get("has_meta_jsonl")),
            "has_summary_json": bool(payload.get("has_summary_json")),
            "analysis": {
                "ocr_available": bool(analysis["ocr"]),
                "showui_available": bool(analysis["showui"]),
                "ocr_jsonl_url": f"/api/runs/{run_id}/analysis/ocr-jsonl" if analysis["ocr"] else None,
                "showui_jsonl_url": f"/api/runs/{run_id}/analysis/showui-jsonl" if analysis["showui"] else None,
            },
            "can_open_folder": True,
            "can_download_sample": True,
        }

    def summary(self, run_id: str) -> dict[str, Any]:
        described = self.describe(run_id)
        return {
            "run_id": run_id,
            "artifact_status": described["artifact_status"],
            "summary": described["summary"],
            "bucket_counts": described["bucket_counts"],
            "has_meta_jsonl": described["has_meta_jsonl"],
            "has_summary_json": described["has_summary_json"],
            "analysis": described["analysis"],
        }

    def samples(self, run_id: str, bucket: str = "low", limit: int = 20) -> list[dict[str, Any]]:
        if bucket not in ALLOWED_BUCKETS:
            raise ValueError("unsupported artifact bucket")
        location = self._resolve_run_location(run_id)
        payload = self._read_remote_artifacts(location)
        meta = payload.get("meta") or []
        selected = self._samples_from_meta(
            meta,
            location=location,
            analysis=self._analysis_lookup(location),
            bucket=bucket,
            limit=max(1, min(limit, 20)),
        )
        return selected

    def thumbnail(self, run_id: str, file_id: str) -> tuple[bytes, str]:
        return self.image(run_id, file_id)

    def image(self, run_id: str, file_id: str) -> tuple[bytes, str]:
        location = self._resolve_run_location(run_id)
        relative_path = self._validate_file_id(file_id)
        extension = relative_path.suffix.lower()
        if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("unsupported image type")
        remote_path = RUN_ROOT / run_id / relative_path
        content = self._cached_remote_file(location, run_id, file_id, remote_path)
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(extension, "image/png")
        return content, content_type

    def analysis_jsonl(self, run_id: str, analysis_type: str) -> bytes:
        location = self._resolve_run_location(run_id)
        if analysis_type == "showui":
            if not SHOWUI_RESULTS_PATH.is_file():
                return b""
            lines = [
                line
                for line in SHOWUI_RESULTS_PATH.read_text(encoding="utf-8").splitlines()
                if self._analysis_line_matches_run(line, run_id)
            ]
            return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        if analysis_type == "ocr":
            try:
                content = self._copy_remote_file(location_for_worker("worker_pc_app_web_w2"), W2_OCR_RESULTS_PATH).decode("utf-8")
                OCR_RESULTS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                OCR_RESULTS_CACHE_PATH.write_text(content, encoding="utf-8")
            except Exception:
                if OCR_RESULTS_CACHE_PATH.is_file():
                    content = OCR_RESULTS_CACHE_PATH.read_text(encoding="utf-8")
                else:
                    return b""
            lines = [line for line in content.splitlines() if self._analysis_line_matches_run(line, run_id)]
            return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        raise ValueError("unsupported analysis type")

    def _cached_remote_file(self, location: RunLocation, run_id: str, file_id: str, remote_path: PureWindowsPath) -> bytes:
        cache_dir = Path("runs/master/artifact_thumbnail_cache").resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.sha256(f"{location.worker_id}:{run_id}:{file_id}".encode("utf-8")).hexdigest()
        cache_path = cache_dir / f"{cache_key}{remote_path.suffix.lower()}"
        if cache_path.exists():
            return cache_path.read_bytes()
        content = self._copy_remote_file(location, remote_path)
        cache_path.write_bytes(content)
        return content

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
        cached = self._read_listing_cache(location)
        if cached is not None:
            return cached
        try:
            return self._fetch_remote_artifacts(location)
        except Exception:
            self._schedule_listing_refresh(location)
            return {
                "status": "refresh_pending",
                "summary": None,
                "meta": [],
                "has_summary_json": False,
                "has_meta_jsonl": False,
                "cache_hit": False,
            }

    def _fetch_remote_artifacts(self, location: RunLocation) -> dict[str, Any]:
        payload = self._run_remote_json(
            location,
            rf"""
$runRoot = "{location.artifact_root}"
$summaryPath = "{PureWindowsPath(location.artifact_root) / "summary.json"}"
$metaPath = "{PureWindowsPath(location.artifact_root) / "meta.jsonl"}"
if (!([IO.Directory]::Exists($runRoot))) {{
  @{{ status = "path_missing"; summary_base64 = $null; meta_base64 = $null; has_summary_json = $false; has_meta_jsonl = $false }} | ConvertTo-Json -Depth 8 -Compress
  exit 0
}}
$summaryExists = [IO.File]::Exists($summaryPath)
$metaExists = [IO.File]::Exists($metaPath)
@{{
  status = "ok"
  summary_base64 = if ($summaryExists) {{ [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([IO.File]::ReadAllText($summaryPath, [Text.Encoding]::UTF8))) }} else {{ $null }}
  meta_base64 = if ($metaExists) {{ [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([IO.File]::ReadAllText($metaPath, [Text.Encoding]::UTF8))) }} else {{ $null }}
  has_summary_json = $summaryExists
  has_meta_jsonl = $metaExists
}} | ConvertTo-Json -Depth 12 -Compress
""",
        )
        summary_text = self._decode_optional_text(payload.get("summary_base64"))
        meta_text = self._decode_optional_text(payload.get("meta_base64"))
        parsed_payload = {
            "status": payload.get("status"),
            "summary": json.loads(summary_text) if summary_text else None,
            "meta": [json.loads(line) for line in meta_text.splitlines() if line.strip()] if meta_text else [],
            "has_summary_json": bool(payload.get("has_summary_json")),
            "has_meta_jsonl": bool(payload.get("has_meta_jsonl")),
        }
        return self._write_listing_cache(location, parsed_payload)

    def _schedule_listing_refresh(self, location: RunLocation) -> None:
        key = self._cache_path(location).stem
        with self._refresh_lock:
            if key in self._refreshing:
                return
            self._refreshing.add(key)

        def refresh() -> None:
            try:
                self._fetch_remote_artifacts(location)
            except Exception:
                pass
            finally:
                with self._refresh_lock:
                    self._refreshing.discard(key)

        thread = threading.Thread(target=refresh, name=f"artifact-refresh-{location.run_id}", daemon=True)
        thread.start()

    def _cache_path(self, location: RunLocation) -> Path:
        cache_key = hashlib.sha256(
            f"{location.worker_id}:{location.worker_host}:{location.run_id}:{location.artifact_root}".encode("utf-8")
        ).hexdigest()
        return self.cache_dir / f"{cache_key}.json"

    def _read_listing_cache(self, location: RunLocation) -> dict[str, Any] | None:
        cache_path = self._cache_path(location)
        try:
            if not cache_path.is_file():
                return None
            if time.time() - cache_path.stat().st_mtime > self.cache_ttl_seconds:
                return None
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if payload.get("status") == "refresh_failed":
                return None
            payload["cache_hit"] = True
            return payload
        except (OSError, json.JSONDecodeError):
            return None

    def _write_listing_cache(self, location: RunLocation, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_payload = {**payload, "cache_hit": False, "cached_at": time.time()}
            self._cache_path(location).write_text(json.dumps(cache_payload, ensure_ascii=False), encoding="utf-8")
            return cache_payload
        except OSError:
            return {**payload, "cache_hit": False}

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
        return self._parse_remote_json_output(result.stdout)

    @staticmethod
    def _parse_remote_json_output(output: str) -> dict[str, Any]:
        decoder = json.JSONDecoder()
        stripped = output.strip()
        candidates = [line.strip() for line in stripped.splitlines() if line.strip()]
        candidates.append(stripped)
        for candidate in candidates:
            if not candidate.startswith("{"):
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise json.JSONDecodeError("remote command did not return a JSON object", stripped, 0)

    def _copy_remote_file(self, location: RunLocation, remote_path: PureWindowsPath) -> bytes:
        handle, temp_name = tempfile.mkstemp()
        os.close(handle)
        Path(temp_name).unlink(missing_ok=True)
        try:
            target = f"{location.ssh_user}@{location.worker_host}:{str(remote_path).replace(chr(92), '/')}"
            result = subprocess.run(
                [
                    "scp",
                    "-q",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=8",
                    target,
                    temp_name,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45,
                check=False,
            )
            if result.returncode != 0:
                raise FileNotFoundError(result.stderr.strip() or str(remote_path))
            return Path(temp_name).read_bytes()
        finally:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _bucket_counts(summary: dict[str, Any], meta: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "fixed": int(summary.get("fixed_count", 0) or 0),
            "low": int(summary.get("low_count", 0) or sum(1 for item in meta if item.get("bucket") == "low" and not item.get("is_duplicate"))),
            "high": int(summary.get("high_count", 0) or 0),
            "rejected": int(summary.get("rejected_count", 0) or 0),
            "duplicates": int(summary.get("duplicate_count", 0) or sum(1 for item in meta if item.get("is_duplicate"))),
        }

    def _samples_from_meta(
        self,
        meta: list[dict[str, Any]],
        location: RunLocation,
        analysis: dict[str, dict[str, dict[str, Any]]],
        bucket: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
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
            capture_method = self._normalized_capture_method(item)
            test_source = self._is_test_source(item)
            content_only = self._content_only(item, capture_method)
            ocr = analysis["ocr"].get(path.name, {})
            showui = analysis["showui"].get(path.name, {})
            samples.append(
                {
                    "file_id": file_id,
                    "file_name": path.name,
                    "artifact_id": file_id,
                    "bucket": display_bucket,
                    "width": int(item.get("width", 0) or 0),
                    "height": int(item.get("height", 0) or 0),
                    "is_duplicate": is_duplicate,
                    "rejected_reason": item.get("rejected_reason"),
                    "thumbnail_url": f"/api/runs/{location.run_id}/artifacts/thumbnail?file_id={file_id}",
                    "image_url": f"/api/runs/{location.run_id}/artifacts/image?file_id={file_id}",
                    "safe_display_path": f"D:\\work\\runs\\<run_id>\\{file_id}",
                    "capture_method": capture_method,
                    "source_method": item.get("source_method"),
                    "test_source": test_source,
                    "production_capture": bool(item.get("production_capture", not test_source)),
                    "content_only": content_only,
                    "browser_chrome_included": item.get("browser_chrome_included", False if content_only else None),
                    "taskbar_included": item.get("taskbar_included", False if content_only else None),
                    "source_type": item.get("source_type"),
                    "source_resolution": self._source_resolution(item),
                    "output_resolution": self._output_resolution(item),
                    "output_width": item.get("output_width", item.get("width")),
                    "output_height": item.get("output_height", item.get("height")),
                    "viewport_width": item.get("viewport_width"),
                    "viewport_height": item.get("viewport_height"),
                    "obs_canvas_width": item.get("obs_canvas_width"),
                    "obs_canvas_height": item.get("obs_canvas_height"),
                    "source_width": item.get("source_width"),
                    "source_height": item.get("source_height"),
                    "device_resolution": item.get("device_resolution"),
                    "window_rect": item.get("window_rect"),
                    "client_rect": item.get("client_rect"),
                    "crop_rect": item.get("crop_rect"),
                    "ocr_status": "available" if ocr else "missing",
                    "detected_text": ocr.get("detected_text"),
                    "text_block_count": ocr.get("text_block_count"),
                    "avg_confidence": ocr.get("avg_confidence"),
                    "ocr_risk_level": ocr.get("risk_level"),
                    "risk_reasons": ocr.get("risk_reasons") or ocr.get("risk_hits"),
                    "ocr_latency_ms": ocr.get("latency_ms"),
                    "ocr_engine": ocr.get("ocr_engine"),
                    "ocr_node": ocr.get("ocr_node"),
                    "showui_status": "available" if showui else "missing",
                    "showui_scene_type": showui.get("scene_type"),
                    "showui_bucket_suggestion": showui.get("bucket_suggestion"),
                    "showui_risk_level": showui.get("risk_level"),
                    "showui_reason": showui.get("reason"),
                    "showui_confidence": showui.get("confidence"),
                    "showui_latency_ms": showui.get("latency_ms"),
                    "showui_provider": showui.get("provider"),
                }
            )
            if len(samples) >= limit:
                break
        return samples

    @staticmethod
    def _normalized_capture_method(item: dict[str, Any]) -> str:
        method = str(item.get("capture_method", "unknown"))
        if method == "playwright_edge_local_html":
            return "playwright_edge_content_only"
        return method

    def _analysis_lookup(self, location: RunLocation) -> dict[str, dict[str, dict[str, Any]]]:
        return {
            "ocr": self._ocr_lookup(location.run_id),
            "showui": self._showui_lookup(location.run_id),
        }

    def _showui_lookup(self, run_id: str) -> dict[str, dict[str, Any]]:
        if not SHOWUI_RESULTS_PATH.is_file():
            return {}
        return self._jsonl_lookup_by_filename(SHOWUI_RESULTS_PATH.read_text(encoding="utf-8"), run_id)

    def _ocr_lookup(self, run_id: str) -> dict[str, dict[str, Any]]:
        if not OCR_RESULTS_CACHE_PATH.is_file():
            return {}
        content = OCR_RESULTS_CACHE_PATH.read_text(encoding="utf-8")
        return self._jsonl_lookup_by_filename(content, run_id)

    @staticmethod
    def _jsonl_lookup_by_filename(content: str, run_id: str) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for line in content.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(item.get("run_id") or "") != run_id:
                continue
            image_path = str(item.get("image_path") or item.get("file_path") or "")
            name = PureWindowsPath(image_path).name
            if name:
                records[name] = item
        return records

    @staticmethod
    def _analysis_line_matches_run(line: str, run_id: str) -> bool:
        try:
            return str(json.loads(line).get("run_id") or "") == run_id
        except json.JSONDecodeError:
            return False

    @staticmethod
    def _is_test_source(item: dict[str, Any]) -> bool:
        if "test_source" in item:
            return bool(item["test_source"])
        return str(item.get("capture_method", "")) == "ffmpeg_testsrc"

    @staticmethod
    def _content_only(item: dict[str, Any], capture_method: str) -> bool | None:
        if "content_only" in item:
            return bool(item["content_only"])
        if capture_method == "playwright_edge_content_only":
            return True
        return None

    @staticmethod
    def _source_resolution(item: dict[str, Any]) -> str:
        if item.get("source_resolution"):
            return str(item["source_resolution"])
        method = str(item.get("capture_method", "unknown"))
        if method == "ffmpeg_testsrc":
            width = int(item.get("width", 0) or 0)
            height = int(item.get("height", 0) or 0)
            return f"{width}x{height} test source"
        if method in {"playwright_edge_local_html", "playwright_edge_content_only"}:
            width = int(item.get("viewport_width", item.get("width", 0)) or 0)
            height = int(item.get("viewport_height", item.get("height", 0)) or 0)
            return f"{width}x{height} page content area"
        if item.get("device_resolution"):
            return f"{item['device_resolution']} device screen"
        if item.get("viewport_width") and item.get("viewport_height"):
            return f"{item['viewport_width']}x{item['viewport_height']} page content area"
        if item.get("source_width") and item.get("source_height"):
            return f"{item['source_width']}x{item['source_height']} source"
        width = int(item.get("width", 0) or 0)
        height = int(item.get("height", 0) or 0)
        return f"{width}x{height}" if width and height else "unknown"

    @staticmethod
    def _output_resolution(item: dict[str, Any]) -> str:
        width = int(item.get("output_width", item.get("width", 0)) or 0)
        height = int(item.get("output_height", item.get("height", 0)) or 0)
        return f"{width}x{height}" if width and height else "unknown"

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

    @staticmethod
    def _decode_optional_text(value: object) -> str:
        if not value:
            return ""
        return base64.b64decode(str(value)).decode("utf-8")
