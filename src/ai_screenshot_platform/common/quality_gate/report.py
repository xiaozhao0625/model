from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from ai_screenshot_platform.common.quality_gate.contracts import ScreenshotQualityResult


@dataclass(frozen=True)
class QualityReportPaths:
    quality_report_path: Path
    clean_manifest_path: Path
    rejected_manifest_path: Path
    ocr_report_path: Path


class QualityReportWriter:
    def write(self, output_dir: Path, results: list[ScreenshotQualityResult]) -> QualityReportPaths:
        output_dir.mkdir(parents=True, exist_ok=True)
        accepted = [result for result in results if result.accepted]
        rejected = [result for result in results if not result.accepted]
        quality_report = {
            "total": len(results),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "ocr_risk_hit_count": sum(result.ocr_risk_hit_count for result in results),
            "reject_reasons": [result.reject_reason for result in rejected],
        }
        quality_report_path = output_dir / "quality_report.json"
        clean_manifest_path = output_dir / "clean_dataset_manifest.jsonl"
        rejected_manifest_path = output_dir / "rejected_quality_manifest.jsonl"
        ocr_report_path = output_dir / "ocr_report.json"
        quality_report_path.write_text(json.dumps(quality_report, ensure_ascii=False, indent=2), encoding="utf-8")
        clean_manifest_path.write_text("".join(json.dumps(asdict(row), ensure_ascii=False) + "\n" for row in accepted), encoding="utf-8")
        rejected_manifest_path.write_text("".join(json.dumps(asdict(row), ensure_ascii=False) + "\n" for row in rejected), encoding="utf-8")
        ocr_report_path.write_text(
            json.dumps({"ocr_risk_hit_count": quality_report["ocr_risk_hit_count"]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return QualityReportPaths(quality_report_path, clean_manifest_path, rejected_manifest_path, ocr_report_path)
