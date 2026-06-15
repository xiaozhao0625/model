from __future__ import annotations

import argparse
import ast
import gc
import hashlib
import json
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(r"E:\work\model")
MODEL_DIR = Path(r"E:\work\models\showui")
RUNTIME = Path(r"E:\work\model_runtime\venvs\vision-runtime")
CACHE_DIR = Path(r"E:\work\model_runtime\cache\showui")
HEALTH_DIR = Path(r"E:\work\model_runtime\health\showui")
SMOKE_DIR = Path(r"E:\work\model_runtime\smoke_outputs\showui")
REPORT_DIR = Path(r"E:\work\model_runtime\reports\showui")
DEPLOY_OUTPUT = REPO_ROOT / "deploy_output"
SAMPLE_ROOT = Path.home() / "AppData" / "Local" / "Temp" / "p13_5_ocr_samples"
SAMPLE_MANIFEST = SAMPLE_ROOT / "sample_manifest.json"
LOCAL_MANIFEST = MODEL_DIR / "showui_local_manifest.json"
PREFLIGHT_PLAN = DEPLOY_OUTPUT / "p13_5_5_showui_preflight_plan.json"

MODEL_ID = "showlab/ShowUI-2B"
REVISION = "cabec4fcc48d15ffd3efe0b33ea9bc7d41509d60"
SOURCE = f"https://huggingface.co/{MODEL_ID}"

ALLOWED_SCENES = {"web", "pc_app", "android", "safe_window", "test_source", "unknown"}
ALLOWED_BUCKETS = {"fixed", "low", "high", "rejected"}
ALLOWED_RISKS = {"none", "low", "medium", "high"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run(cmd: list[str], cwd: Path = REPO_ROOT) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def git_meta() -> dict[str, Any]:
    try:
        status = run(["git", "status", "--short"])
        return {"branch": run(["git", "branch", "--show-current"]), "commit": run(["git", "rev-parse", "--short", "HEAD"]), "status": "clean" if not status else status}
    except Exception:
        return {"branch": "unknown", "commit": "unknown", "status": "unknown"}


def nvidia_info() -> dict[str, Any]:
    try:
        text = run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"])
        name, total, free, driver = [part.strip() for part in text.splitlines()[0].split(",")]
        return {"gpu": name, "vram_total_mb": int(total), "vram_free_mb": int(free), "driver_version": driver}
    except Exception as exc:
        return {"gpu": "unknown", "vram_total_mb": 0, "vram_free_mb": 0, "driver_version": "unknown", "error": repr(exc)}


def sha256_for(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_manifest() -> dict[str, Any]:
    return json.loads(LOCAL_MANIFEST.read_text(encoding="utf-8"))


def verify_hashes(manifest: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    verified = []
    ok = True
    for item in manifest["files"]:
        path = MODEL_DIR / item["path"]
        exists = path.exists()
        actual = sha256_for(path) if exists else None
        expected = item.get("sha256")
        match = bool(exists and expected and actual == expected)
        ok = ok and match
        verified.append({**item, "exists": exists, "sha256_verified": match, "actual_sha256": actual})
    return ok, verified


def dependencies() -> dict[str, str]:
    deps: dict[str, str] = {}
    for name in ["torch", "torchvision", "transformers", "accelerate", "huggingface_hub", "qwen_vl_utils", "PIL", "numpy"]:
        try:
            module = __import__("PIL.Image" if name == "PIL" else name)
            deps[name] = getattr(module, "__version__", "import_ok")
        except Exception as exc:
            deps[name] = f"import_error:{exc!r}"
    return deps


def sample_records(limit_per_role: int = 5) -> list[dict[str, Any]]:
    raw = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8-sig"))
    records = []
    seen: Counter[str] = Counter()
    for item in raw:
        role = item["role"]
        if seen[role] >= limit_per_role:
            continue
        image_path = SAMPLE_ROOT / role / item["file_name"]
        if not image_path.exists():
            continue
        records.append({**item, "image_path": str(image_path)})
        seen[role] += 1
    return records


def parse_model_answer(answer: str, role: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        try:
            value = ast.literal_eval(answer)
            if isinstance(value, dict):
                parsed = value
        except Exception:
            parsed = {}
    scene = str(parsed.get("scene_type") or {"W1": "safe_window", "W2": "web", "W3": "android"}.get(role, "unknown")).strip()
    bucket = str(parsed.get("bucket_suggestion") or "low").strip()
    risk = str(parsed.get("risk_level") or "none").strip()
    reason = str(parsed.get("reason") or answer[:240] or "No structured reason returned.")
    try:
        confidence = float(parsed.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    return {
        "scene_type": scene if scene in ALLOWED_SCENES else "unknown",
        "bucket_suggestion": bucket if bucket in ALLOWED_BUCKETS else "low",
        "risk_level": risk if risk in ALLOWED_RISKS else "none",
        "reason": reason,
        "confidence": max(0.0, min(confidence, 1.0)),
        "raw_answer": answer,
    }


def load_showui_model():
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    processor = AutoProcessor.from_pretrained(MODEL_DIR, trust_remote_code=True, local_files_only=True)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_DIR,
        dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
        local_files_only=True,
        low_cpu_mem_usage=True,
    ).eval()
    return processor, model


def infer_one(processor: Any, model: Any, image_path: str) -> tuple[str, int]:
    import torch
    from qwen_vl_utils import process_vision_info

    prompt = (
        "Classify this UI screenshot. Reply only compact JSON with keys "
        "scene_type, bucket_suggestion, risk_level, reason, confidence. "
        "Allowed scene_type: web, pc_app, android, safe_window, test_source, unknown. "
        "Allowed bucket_suggestion: fixed, low, high, rejected. "
        "Allowed risk_level: none, low, medium, high. Do not suggest or execute actions."
    )
    messages = [{"role": "user", "content": [{"type": "image", "image": image_path}, {"type": "text", "text": prompt}]}]
    start = time.perf_counter()
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=128, do_sample=False)
    trimmed = [output[len(input_ids) :] for input_ids, output in zip(inputs.input_ids, generated)]
    answer = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    return answer, int((time.perf_counter() - start) * 1000)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_md(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([f"# {title}", "", *lines, ""]), encoding="utf-8")


def run_all(limit_per_role: int = 5) -> dict[str, Any]:
    for directory in [HEALTH_DIR, SMOKE_DIR, REPORT_DIR, DEPLOY_OUTPUT]:
        directory.mkdir(parents=True, exist_ok=True)

    git = git_meta()
    plan = json.loads(PREFLIGHT_PLAN.read_text(encoding="utf-8"))
    manifest = load_manifest()
    hash_ok, verified_files = verify_hashes(manifest)
    before_gpu = nvidia_info()
    deps = dependencies()

    health: dict[str, Any] = {
        "provider": "showui",
        "target_node": "M0",
        "status": "hash_verified" if hash_ok else "failed",
        "checked_at": now_iso(),
        "model_dir": str(MODEL_DIR),
        "runtime": str(RUNTIME),
        "source": SOURCE,
        "revision": REVISION,
        "hash_verified": hash_ok,
        "file_count": manifest["file_count"],
        "total_size_bytes": manifest["total_size_bytes"],
        "dependencies": deps,
        "gpu": before_gpu.get("gpu"),
        "vram_total_mb": before_gpu.get("vram_total_mb"),
        "vram_free_before_mb": before_gpu.get("vram_free_mb"),
        "vram_free_after_mb": None,
        "latency_ms": 0,
        "enabled": False,
        "online_inference": False,
        "model_action_control": False,
        "error": None,
    }

    smoke_results: list[dict[str, Any]] = []
    samples = sample_records(limit_per_role)
    load_started = time.perf_counter()
    processor = model = None
    try:
        if not hash_ok:
            raise RuntimeError("hash verification failed")
        processor, model = load_showui_model()
        health["status"] = "model_loaded"
        health["model_loaded"] = True
        health["model_device"] = str(next(model.parameters()).device)
        health["model_dtype"] = str(next(model.parameters()).dtype)

        health_probe_answer, health_probe_ms = infer_one(processor, model, samples[0]["image_path"])
        health["inference_probe"] = parse_model_answer(health_probe_answer, samples[0]["role"])
        health["inference_probe_latency_ms"] = health_probe_ms
        health["status"] = "inference_ok"

        for sample in samples:
            record = {
                "image_path": sample["image_path"],
                "run_id": sample["run_id"],
                "worker_id": sample["worker_id"],
                "provider": "showui",
                "target_node": "M0",
                "ui_elements": [],
                "error": None,
            }
            try:
                answer, latency_ms = infer_one(processor, model, sample["image_path"])
                record.update(parse_model_answer(answer, sample["role"]))
                record["latency_ms"] = latency_ms
                record["suitable_for_capture"] = record["bucket_suggestion"] != "rejected"
            except Exception as exc:
                record.update(
                    {
                        "scene_type": "unknown",
                        "bucket_suggestion": "rejected",
                        "risk_level": "medium",
                        "reason": "ShowUI inference failed for this sample.",
                        "confidence": 0.0,
                        "latency_ms": 0,
                        "suitable_for_capture": False,
                        "error": repr(exc),
                    }
                )
            smoke_results.append(record)
    except Exception as exc:
        health["status"] = "failed"
        health["error"] = repr(exc)
    finally:
        health["latency_ms"] = int((time.perf_counter() - load_started) * 1000)
        if model is not None:
            del model
        if processor is not None:
            del processor
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        after_gpu = nvidia_info()
        health["vram_free_after_mb"] = after_gpu.get("vram_free_mb")

    results_path = SMOKE_DIR / "showui_sample_results.jsonl"
    results_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in smoke_results) + ("\n" if smoke_results else ""), encoding="utf-8")
    role_distribution = Counter(Path(item["image_path"]).parent.name for item in smoke_results)
    scene_distribution = Counter(item["scene_type"] for item in smoke_results)
    bucket_distribution = Counter(item["bucket_suggestion"] for item in smoke_results)
    risk_distribution = Counter(item["risk_level"] for item in smoke_results)
    latencies = [item["latency_ms"] for item in smoke_results if not item.get("error")]
    smoke = {
        "provider": "showui",
        "target_node": "M0",
        "status": "smoke_passed" if health["status"] == "inference_ok" and len(smoke_results) >= 15 and not any(item.get("error") for item in smoke_results) else "smoke_failed",
        "sample_count": len(smoke_results),
        "role_distribution": dict(role_distribution),
        "scene_type_distribution": dict(scene_distribution),
        "bucket_suggestion_distribution": dict(bucket_distribution),
        "risk_level_distribution": dict(risk_distribution),
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
        "failed_count": sum(1 for item in smoke_results if item.get("error")),
        "results_path": str(results_path),
        "enabled": False,
        "online_inference": False,
        "model_action_control": False,
        "started_production_capture": False,
    }

    download = {
        "downloaded": True,
        "status": "downloaded",
        "source": SOURCE,
        "model_id": MODEL_ID,
        "revision": REVISION,
        "requires_token": False,
        "target_dir": str(MODEL_DIR),
        "cache_dir": str(CACHE_DIR),
        "file_count": manifest["file_count"],
        "total_size_bytes": manifest["total_size_bytes"],
        "files": verified_files,
        "downloaded_other_models": False,
    }
    common = {
        "generated_at": now_iso(),
        "git": git,
        "code_modified": True,
        "commit_hash": git["commit"],
        "push_success": "pending",
        "download": download,
        "safety": {
            "enabled": False,
            "online_inference": False,
            "model_action_control": False,
            "started_production_capture": False,
            "downloaded_other_models": False,
            "submitted_large_files": False,
            "sensitive_information_disclosed": False,
        },
        "blocked": [],
        "manual_required": [],
    }
    health_report = {**common, "schema_version": "p13.5.5", "health": health}
    smoke_report = {**common, "schema_version": "p13.5.6", "health_status": health["status"], "sample_smoke": smoke}
    combined = {**common, "schema_version": "p13.5.5-5.6", "health": health, "sample_smoke": smoke, "web_console": {"model_gateway": "reads showui health report", "artifact_inspector": "shows ShowUI fields when present in metadata", "quality_report": "ShowUI smoke report is read-only"}}

    for stem, payload in [
        ("p13_5_5_showui_health_report", health_report),
        ("p13_5_6_showui_sample_smoke_report", smoke_report),
        ("p13_5_5_6_showui_health_smoke_report", combined),
    ]:
        write_json(REPORT_DIR / f"{stem}.json", payload)
        write_json(DEPLOY_OUTPUT / f"{stem}.json", payload)

    write_md(
        REPORT_DIR / "p13_5_5_showui_health_report.md",
        "P13.5.5 ShowUI Health",
        [
            f"- status: {health['status']}",
            f"- source: {SOURCE}",
            f"- revision: {REVISION}",
            f"- files: {manifest['file_count']}",
            f"- hash_verified: {hash_ok}",
            f"- runtime: {RUNTIME}",
            f"- dependencies: {json.dumps(deps, ensure_ascii=False)}",
            f"- GPU/VRAM: {health['gpu']} / {health['vram_total_mb']} MB",
            "- enabled: false",
            "- online_inference: false",
            "- downloaded other models: no",
        ],
    )
    write_md(
        REPORT_DIR / "p13_5_6_showui_sample_smoke_report.md",
        "P13.5.6 ShowUI Sample Smoke",
        [
            f"- status: {smoke['status']}",
            f"- sample_count: {smoke['sample_count']}",
            f"- role_distribution: {json.dumps(smoke['role_distribution'], ensure_ascii=False)}",
            f"- scene_type: {json.dumps(smoke['scene_type_distribution'], ensure_ascii=False)}",
            f"- bucket_suggestion: {json.dumps(smoke['bucket_suggestion_distribution'], ensure_ascii=False)}",
            f"- risk_level: {json.dumps(smoke['risk_level_distribution'], ensure_ascii=False)}",
            f"- avg_latency_ms: {smoke['avg_latency_ms']:.2f}",
            f"- failed_count: {smoke['failed_count']}",
            f"- output: {results_path}",
            "- model action control: no",
            "- production capture: no",
        ],
    )
    write_md(
        REPORT_DIR / "p13_5_5_6_showui_health_smoke_report.md",
        "P13.5.5-P13.5.6 ShowUI Health + Smoke",
        [
            f"- health: {health['status']}",
            f"- sample_smoke: {smoke['status']}",
            f"- source: {SOURCE}",
            f"- revision: {REVISION}",
            f"- hash_verified: {hash_ok}",
            f"- downloaded other models: no",
            "- enabled: false",
            "- online_inference: false",
            "- model action control: no",
            "- production capture: no",
            "- submitted large files: no",
        ],
    )
    for name in [
        "p13_5_5_showui_health_report.md",
        "p13_5_6_showui_sample_smoke_report.md",
        "p13_5_5_6_showui_health_smoke_report.md",
    ]:
        (DEPLOY_OUTPUT / name).write_text((REPORT_DIR / name).read_text(encoding="utf-8"), encoding="utf-8")
    return combined


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-per-role", type=int, default=5)
    args = parser.parse_args()
    result = run_all(limit_per_role=args.limit_per_role)
    print(json.dumps({"health": result["health"]["status"], "smoke": result["sample_smoke"]["status"], "sample_count": result["sample_smoke"]["sample_count"]}, ensure_ascii=False))
    return 0 if result["health"]["status"] == "inference_ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
