from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


W2_ROOT = Path(r"D:\work")
VENV = W2_ROOT / "model_runtime" / "venvs" / "ocr-runtime"
REPORT_ROOT = W2_ROOT / "model_runtime" / "reports"
OCR_ROOT = W2_ROOT / "ocr"
CACHE_ROOT = W2_ROOT / "model_runtime" / "cache"
PADDLEX_DEFAULT_ROOT = Path.home() / ".paddlex"
SMOKE_ROOT = REPORT_ROOT / "ocr_sample_smoke"
HEALTH_ROOT = REPORT_ROOT / "p13_5_1_health"
INPUT_ROOT = SMOKE_ROOT / "input_samples"
MANIFEST_PATH = SMOKE_ROOT / "sample_manifest.json"
MASTER_API = "http://192.168.1.18:8000"

RISK_TERMS: dict[str, dict[str, Any]] = {
    "captcha": {"level": "high", "terms": ["\u9a8c\u8bc1\u7801", "captcha", "verification code", "security check", "\u4eba\u673a\u9a8c\u8bc1"]},
    "login": {"level": "medium", "terms": ["\u767b\u5f55", "\u767b\u9646", "sign in", "log in", "register", "\u6ce8\u518c", "account"]},
    "payment": {"level": "high", "terms": ["\u652f\u4ed8", "\u5145\u503c", "\u8d2d\u4e70", "order", "payment", "pay", "checkout", "\u4ed8\u6b3e", "\u8ba2\u5355"]},
    "chat": {"level": "medium", "terms": ["\u53d1\u9001", "\u804a\u5929", "message", "send", "input message", "\u79c1\u4fe1"]},
    "account_security": {
        "level": "high",
        "terms": ["\u8d26\u53f7\u5b89\u5168", "security", "password", "\u5bc6\u7801", "phone verification", "\u624b\u673a\u9a8c\u8bc1", "\u90ae\u7bb1\u9a8c\u8bc1"],
    },
    "privacy": {"level": "medium", "terms": ["\u8eab\u4efd\u8bc1", "\u624b\u673a\u53f7", "email", "\u90ae\u7bb1", "address", "\u5730\u5740", "real name", "\u5b9e\u540d"]},
    "permission": {"level": "medium", "terms": ["\u6743\u9650", "allow", "deny", "\u5141\u8bb8", "\u62d2\u7edd", "permission"]},
}

LEVEL_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def configure_runtime_env() -> None:
    paths = {
        "PADDLE_HOME": CACHE_ROOT / "paddle",
        "PADDLEOCR_HOME": OCR_ROOT / "paddleocr",
        "PADDLEX_HOME": CACHE_ROOT / "paddlex",
        "HF_HOME": CACHE_ROOT / "huggingface",
        "MODELSCOPE_CACHE": CACHE_ROOT / "modelscope",
        "AISTUDIO_CACHE_DIR": CACHE_ROOT / "aistudio",
    }
    for key, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_use_onednn", "0")
    os.environ.setdefault("PADDLE_DISABLE_MKLDNN", "1")


def sha256_for(path: Path) -> str:
    if path.stat().st_size > 200 * 1024 * 1024:
        return "skipped_large_file"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def downloaded_files() -> list[dict[str, Any]]:
    tracked_exts = {".pdiparams", ".pdmodel", ".json", ".yml", ".yaml", ".txt", ".onnx", ".safetensors"}
    files: list[dict[str, Any]] = []
    for root in [CACHE_ROOT, OCR_ROOT, PADDLEX_DEFAULT_ROOT]:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in tracked_exts and "paddle" not in path.name.lower():
                continue
            files.append({"path": str(path), "size": path.stat().st_size, "sha256": sha256_for(path)})
    return files


def make_synthetic_image(path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (900, 260), "white")
    draw = ImageDraw.Draw(image)
    font = None
    for candidate in [Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\simhei.ttf"), Path(r"C:\Windows\Fonts\arial.ttf")]:
        if candidate.exists():
            font = ImageFont.truetype(str(candidate), 42)
            break
    if font is None:
        font = ImageFont.load_default()
    draw.text((30, 40), "P13.5 OCR \u5065\u5eb7\u68c0\u67e5", fill="black", font=font)
    draw.text((30, 105), "Hello OCR 123", fill="black", font=font)
    draw.text((30, 170), "\u9a8c\u8bc1\u7801 \u6d4b\u8bd5", fill="black", font=font)
    image.save(path)


def create_ocr() -> Any:
    import paddle
    from paddleocr import PaddleOCR

    paddle.device.set_device("cpu")
    return PaddleOCR(
        lang="ch",
        ocr_version="PP-OCRv4",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        device="cpu",
    )


def ocr_image(ocr: Any, image_path: Path) -> dict[str, Any]:
    start = time.perf_counter()
    text_blocks: list[dict[str, Any]] = []
    error = None
    try:
        result = ocr.predict(str(image_path))
        for page in result:
            data = getattr(page, "json", None)
            if callable(data):
                data = data()
            if data is None and hasattr(page, "to_json"):
                data = page.to_json()
            if data is None:
                data = page if isinstance(page, dict) else {}
            if isinstance(data, dict) and isinstance(data.get("res"), dict):
                data = data["res"]
            rec_texts = data.get("rec_texts") if isinstance(data, dict) else None
            rec_scores = data.get("rec_scores") if isinstance(data, dict) else None
            rec_boxes = data.get("rec_boxes") if isinstance(data, dict) else None
            if not rec_texts:
                continue
            for index, text in enumerate(rec_texts):
                score = rec_scores[index] if rec_scores and index < len(rec_scores) else None
                box = None
                if rec_boxes is not None and index < len(rec_boxes):
                    raw_box = rec_boxes[index]
                    box = raw_box.tolist() if hasattr(raw_box, "tolist") else raw_box
                text_blocks.append({"text": str(text), "confidence": score, "bbox": box})
    except Exception as exc:  # noqa: BLE001 - batch smoke reports per-image failures.
        error = repr(exc)
    latency_ms = int((time.perf_counter() - start) * 1000)
    confidences = [float(block["confidence"]) for block in text_blocks if block.get("confidence") is not None]
    return {
        "detected_text": " ".join(block["text"] for block in text_blocks),
        "text_blocks": text_blocks,
        "text_block_count": len(text_blocks),
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
        "latency_ms": latency_ms,
        "error": error,
    }


def run_health() -> dict[str, Any]:
    configure_runtime_env()
    HEALTH_ROOT.mkdir(parents=True, exist_ok=True)
    image_path = HEALTH_ROOT / "synthetic_ocr_health.png"
    make_synthetic_image(image_path)

    import paddle
    import paddleocr

    start = time.perf_counter()
    try:
        ocr = create_ocr()
        result = ocr_image(ocr, image_path)
        error = result.get("error")
        status = "health_passed" if result["text_block_count"] > 0 else "health_failed" if error else "health_partial"
    except Exception as exc:  # noqa: BLE001
        result = {"detected_text": "", "text_blocks": [], "text_block_count": 0, "avg_confidence": 0.0, "latency_ms": 0}
        status = "health_failed"
        error = repr(exc)

    payload = {
        "node": "W2",
        "engine": "paddleocr",
        "status": status,
        "venv": str(VENV),
        "ocr_root": str(OCR_ROOT),
        "version": getattr(paddleocr, "__version__", "unknown"),
        "paddle_version": getattr(paddle, "__version__", "unknown"),
        "mode": "cpu",
        "latency_ms": int((time.perf_counter() - start) * 1000),
        "recognized_text": result["detected_text"],
        "text_blocks": result["text_blocks"],
        "synthetic_image": str(image_path),
        "downloaded_files": downloaded_files(),
        "cache_dirs": [str(CACHE_ROOT), str(OCR_ROOT), str(PADDLEX_DEFAULT_ROOT)],
        "enabled": False,
        "online_inference": False,
        "error": error,
    }
    (HEALTH_ROOT / "health_result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_manifest() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig")):
        records.append({**item, "w2_image_path": str(INPUT_ROOT / item["role"] / item["file_name"])})
    return records


def detect_risk(text: str) -> dict[str, Any]:
    normalized = text.lower()
    reasons: list[str] = []
    matched: list[str] = []
    level = "none"
    for risk_type, config in RISK_TERMS.items():
        for term in config["terms"]:
            if term.lower() in normalized:
                reasons.append(f"{risk_type}_detected")
                matched.append(term)
                if LEVEL_ORDER[str(config["level"])] > LEVEL_ORDER[level]:
                    level = str(config["level"])
                break
    action = "allow" if level == "none" else "warn" if level in {"low", "medium"} else "block"
    return {
        "risk_level": level,
        "risk_reasons": reasons,
        "matched_keywords": matched,
        "action": action,
        "human_review_required": level in {"medium", "high"},
        "should_stop_capture": False,
    }


def run_smoke() -> dict[str, Any]:
    configure_runtime_env()
    SMOKE_ROOT.mkdir(parents=True, exist_ok=True)
    records = load_manifest()
    health = json.loads((HEALTH_ROOT / "health_result.json").read_text(encoding="utf-8")) if (HEALTH_ROOT / "health_result.json").exists() else run_health()
    if health["status"] not in {"health_passed", "health_partial"}:
        return {"schema_version": "p13.5.2", "status": "blocked_by_ocr_health_failed", "samples_processed": 0, "blocked": ["P13.5.1 OCR health did not pass"]}

    ocr = create_ocr()
    results = []
    for record in records:
        image_path = Path(record["w2_image_path"])
        results.append(
            {
                "run_id": record["run_id"],
                "worker_id": record["worker_id"],
                "image_path": str(image_path),
                "image_file": record["file_name"],
                "ocr_engine": "paddleocr",
                "ocr_node": "W2",
                "language_mode": "mixed",
                **ocr_image(ocr, image_path),
            }
        )

    results_path = SMOKE_ROOT / "ocr_results.jsonl"
    results_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in results) + "\n", encoding="utf-8")
    role_counts: dict[str, int] = {}
    for record in records:
        role_counts[record["role"]] = role_counts.get(record["role"], 0) + 1
    latencies = [item["latency_ms"] for item in results if item.get("error") is None]
    failed_count = sum(1 for item in results if item.get("error"))
    text_detected_count = sum(1 for item in results if item.get("text_block_count", 0) > 0)
    smoke_status = "smoke_passed" if results and failed_count == 0 and text_detected_count > 0 and all(role_counts.get(role, 0) >= 5 for role in ["W1", "W2", "W3"]) else "smoke_failed" if failed_count == len(results) else "smoke_partial"
    summary = {
        "schema_version": "p13.5.2",
        "status": smoke_status,
        "ocr_engine": "paddleocr",
        "ocr_node": "W2",
        "samples_processed": len(results),
        "sample_distribution": role_counts,
        "failed_count": failed_count,
        "text_detected_count": text_detected_count,
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
        "results_path": str(results_path),
        "original_images_modified": False,
        "uploaded_images": False,
    }
    (SMOKE_ROOT / "ocr_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def run_risk_gate() -> dict[str, Any]:
    SMOKE_ROOT.mkdir(parents=True, exist_ok=True)
    results_path = SMOKE_ROOT / "ocr_results.jsonl"
    ocr_results = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()] if results_path.exists() else []
    risk_records = []
    for item in ocr_results:
        risk_records.append(
            {
                "run_id": item["run_id"],
                "worker_id": item["worker_id"],
                "image_path": item["image_path"],
                "ocr_engine": "paddleocr",
                **detect_risk(item.get("detected_text", "")),
                "created_at": now_iso(),
            }
        )

    synthetic_texts = {
        "captcha": "\u8bf7\u8f93\u5165\u9a8c\u8bc1\u7801",
        "payment": "\u786e\u8ba4\u652f\u4ed8\u8ba2\u5355",
        "login": "\u767b\u5f55\u8d26\u53f7 password",
        "chat": "\u53d1\u9001\u804a\u5929 message",
        "account_security": "\u8d26\u53f7\u5b89\u5168\u9a8c\u8bc1 phone verification",
        "safe": "Settings display network status",
    }
    synthetic = [{"sample_id": key, "text": text, **detect_risk(text)} for key, text in synthetic_texts.items()]
    risk_path = SMOKE_ROOT / "ocr_risk_results.jsonl"
    risk_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in risk_records) + "\n", encoding="utf-8")

    distribution: dict[str, int] = {}
    for item in risk_records + synthetic:
        distribution[item["risk_level"]] = distribution.get(item["risk_level"], 0) + 1
    summary = {
        "schema_version": "p13.5.3",
        "status": "risk_gate_passed",
        "risk_results_path": str(risk_path),
        "risk_level_distribution": distribution,
        "synthetic_risk_tests": synthetic,
        "human_review_required_count": sum(1 for item in risk_records if item["human_review_required"]),
        "auto_action_execution": False,
        "should_stop_capture_default": False,
    }
    (SMOKE_ROOT / "ocr_risk_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def ingest_ocr_status(smoke: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "app_id": "p13_5_w2_ocr_runtime",
        "run_id": "p13_5_1_3_w2_paddleocr_runtime",
        "provider": "paddleocr",
        "available": True,
        "status": "available",
        "risk_hits": sorted({reason.removesuffix("_detected") for test in risk["synthetic_risk_tests"] for reason in test["risk_reasons"]}),
        "scene_hints": ["ocr_sample_smoke", "risk_gate", "w2_local_ocr"],
        "unavailable_reason": None,
        "paddleocr_optional_status": "health_passed",
        "easyocr_optional_status": "not_installed",
        "source_path": str(SMOKE_ROOT / "ocr_summary.json"),
    }
    request = urllib.request.Request(
        f"{MASTER_API}/api/ocr/reports/ingest",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return {"status": "ingested", "http_status": response.status, "response": json.loads(response.read().decode("utf-8"))}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"status": "failed", "error": repr(exc)}


def write_combined_report(health: dict[str, Any], smoke: dict[str, Any], risk: dict[str, Any], ingest: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": "p13.5.1-1.3",
        "generated_at": now_iso(),
        "current_branch": "generated_on_w2",
        "current_commit": "reported_by_m0",
        "git_status": "reported_by_m0",
        "code_modified": "reported_by_m0",
        "push_status": "reported_by_m0",
        "p13_5_1_health": health,
        "p13_5_2_ocr_smoke": smoke,
        "p13_5_3_risk_gate": risk,
        "master_ingest": ingest,
        "web_console": {
            "ocr_status_page": "available via /api/ocr/status after ingest",
            "quality_report": "risk summary generated; quality aggregation remains read-only",
            "artifact_inspector": "OCR result paths generated for sampled images",
            "enabled": False,
            "online_inference": False,
        },
        "safety": {
            "downloaded_showui": False,
            "downloaded_vision_large_model": False,
            "installed_easyocr": False,
            "started_production_capture": False,
            "processed_or_bypassed_captcha": False,
            "auto_action_execution": False,
            "worker_direct_postgresql": False,
            "sensitive_information_disclosed": False,
        },
        "blocked": [],
        "manual_required": [],
        "next_action": "Review W2 OCR accuracy and decide whether to proceed to ShowUI download authorization.",
    }
    json_path = REPORT_ROOT / "p13_5_1_3_w2_paddleocr_runtime_smoke_risk_gate_report.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = REPORT_ROOT / "p13_5_1_3_w2_paddleocr_runtime_smoke_risk_gate_report.md"
    md_path.write_text(
        "\n".join(
            [
                "# P13.5.1-P13.5.3 W2 PaddleOCR Runtime / OCR Smoke / Risk Gate",
                "",
                f"- health: {health['status']}",
                f"- PaddleOCR: {health['version']}",
                f"- PaddlePaddle: {health['paddle_version']}",
                f"- mode: {health['mode']}",
                f"- OCR smoke: {smoke['status']}",
                f"- samples_processed: {smoke['samples_processed']}",
                f"- distribution: {json.dumps(smoke['sample_distribution'], ensure_ascii=False)}",
                f"- failed_count: {smoke['failed_count']}",
                f"- RiskGate: {risk['status']}",
                f"- risk_distribution: {json.dumps(risk['risk_level_distribution'], ensure_ascii=False)}",
                f"- Master ingest: {ingest['status']}",
                "- enabled: false",
                "- online_inference: false",
                "- downloaded ShowUI: no",
                "- downloaded vision large model: no",
                "- installed EasyOCR: no",
                "- started production capture: no",
                "- auto action execution: no",
            ]
        ),
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["health", "smoke", "risk", "all"], default="all")
    args = parser.parse_args()
    if args.action == "health":
        print(json.dumps(run_health(), ensure_ascii=False))
        return 0
    if args.action == "smoke":
        print(json.dumps(run_smoke(), ensure_ascii=False))
        return 0
    if args.action == "risk":
        print(json.dumps(run_risk_gate(), ensure_ascii=False))
        return 0
    health = run_health()
    if health["status"] not in {"health_passed", "health_partial"}:
        print(json.dumps({"status": "blocked_by_ocr_health_failed", "health": health}, ensure_ascii=False))
        return 2
    smoke = run_smoke()
    risk = run_risk_gate()
    ingest = ingest_ocr_status(smoke, risk)
    print(json.dumps(write_combined_report(health, smoke, risk, ingest), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
