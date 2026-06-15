from __future__ import annotations

from ai_screenshot_platform.master.repositories.production_readiness_repo import (
    ProductionReadinessRepo,
)


class ProductionReadinessService:
    def __init__(self, repo: ProductionReadinessRepo) -> None:
        self.repo = repo

    def ingest_quality_report(self, payload: dict):
        return self.repo.upsert_quality_report(payload)

    def list_quality_reports(self):
        return self.repo.list_quality_reports()

    def get_quality_report(self, run_id: str):
        return self.repo.get_quality_report(run_id)

    def ingest_ocr_report(self, payload: dict):
        return self.repo.upsert_ocr_report(payload)

    def list_ocr_reports(self):
        return self.repo.list_ocr_reports()

    def get_ocr_report(self, run_id: str):
        return self.repo.get_ocr_report(run_id)

    def latest_ocr_status(self):
        return self.repo.latest_ocr_status()

    def model_deployment_matrix(self):
        return {
            "schema_version": "p13.5.0",
            "status": "planned_only",
            "online_inference_enabled": False,
            "model_downloaded": False,
            "ocr_installed": False,
            "scheduler_rules": {
                "local_first": True,
                "m0_fallback": True,
                "idle_only": True,
                "worker_direct_postgresql": False,
                "production_capture_assist_enabled": False,
            },
            "providers": [
                {
                    "provider": "showui",
                    "target_node": "M0",
                    "candidate_nodes": ["W2", "W3"],
                    "download_status": "planned",
                    "hash_verification": "not_available",
                    "health_status": "missing_weights",
                    "enabled": False,
                    "online_inference_enabled": False,
                    "estimated_vram_gb": "4-6",
                    "last_health_at": None,
                    "model_dir": r"E:\work\models\showui",
                    "runtime_dir": r"E:\work\model_runtime\venvs\vision-runtime",
                },
                {
                    "provider": "omniparser",
                    "target_node": "M0",
                    "candidate_nodes": ["W2"],
                    "download_status": "planned_fallback",
                    "hash_verification": "not_available",
                    "health_status": "not_configured",
                    "enabled": False,
                    "online_inference_enabled": False,
                    "estimated_vram_gb": "6-8",
                    "last_health_at": None,
                    "model_dir": r"E:\work\models\omniparser",
                    "runtime_dir": r"E:\work\model_runtime\venvs\vision-runtime",
                },
            ],
            "nodes": [
                {
                    "role": "M0",
                    "ip": "192.168.1.18",
                    "gpu": "RTX 5060Ti",
                    "vram_gb": 16,
                    "models_dir": r"E:\work\models",
                    "ocr_dir": r"E:\work\ocr",
                    "runtime_dir": r"E:\work\model_runtime",
                    "capabilities": ["central_model_gateway", "heavy_vlm", "central_ocr", "offline_batch_analysis"],
                    "planned_components": ["central OCR", "heavy VLM", "OmniParser/ShowUI", "offline batch analysis"],
                    "estimated_vram_gb": "6-14",
                    "capture_impact": "none, control plane only",
                    "enabled": False,
                },
                {
                    "role": "W1",
                    "ip": "192.168.1.34",
                    "gpu": "RTX 3060",
                    "vram_gb": 12,
                    "models_dir": r"D:\work\models",
                    "ocr_dir": r"D:\work\ocr",
                    "runtime_dir": r"D:\work\model_runtime",
                    "capabilities": ["pc_game_capture_priority", "local_ocr_optional", "light_model_optional", "idle_only"],
                    "planned_components": ["optional OCR", "optional light sampling"],
                    "estimated_vram_gb": "0-2 idle-only",
                    "capture_impact": "must not affect OBS/FFmpeg/game capture",
                    "enabled": False,
                },
                {
                    "role": "W2",
                    "ip": "192.168.1.20",
                    "gpu": "RTX 3060",
                    "vram_gb": 12,
                    "models_dir": r"D:\work\models",
                    "ocr_dir": r"D:\work\ocr",
                    "runtime_dir": r"D:\work\model_runtime",
                    "capabilities": ["local_ocr", "ui_parser", "web_pc_app_analysis", "light_model"],
                    "planned_components": ["local OCR", "UI parser", "light model"],
                    "estimated_vram_gb": "2-6 idle-aware",
                    "capture_impact": "local analysis only when capture is idle or safe",
                    "enabled": False,
                },
                {
                    "role": "W3",
                    "ip": "192.168.1.21",
                    "gpu": "RTX 3060",
                    "vram_gb": 12,
                    "models_dir": r"D:\work\models",
                    "ocr_dir": r"D:\work\ocr",
                    "runtime_dir": r"D:\work\model_runtime",
                    "capabilities": ["local_ocr", "android_ui_parser", "light_model", "m0_heavy_fallback"],
                    "planned_components": ["Android OCR", "Android UI parser", "light model"],
                    "estimated_vram_gb": "2-4 when emulator is not busy",
                    "capture_impact": "must not affect Android emulator/ADB flow",
                    "enabled": False,
                },
            ],
        }

    def ingest_tool_health(self, payload: dict):
        return self.repo.ingest_tool_health(payload)

    def tool_health(self):
        return self.repo.tool_health()

    def worker_tool_health(self):
        return self.repo.tool_health()

    def android_tool_health(self):
        return self.repo.android_runtime()

    def ingest_behavior_candidate(self, payload: dict):
        return self.repo.upsert_behavior_candidate(payload)

    def list_behavior_candidates(self):
        return self.repo.list_behavior_candidates()

    def get_behavior_candidate(self, candidate_pack_id: str):
        return self.repo.get_behavior_candidate(candidate_pack_id)

    def approve_behavior_candidate(self, candidate_pack_id: str, reviewer: str | None, reason: str | None):
        return self.repo.review_candidate(candidate_pack_id, "approved", reviewer, reason)

    def reject_behavior_candidate(self, candidate_pack_id: str, reviewer: str | None, reason: str | None):
        return self.repo.review_candidate(candidate_pack_id, "rejected", reviewer, reason)

    def rollback_behavior_candidate(self, candidate_pack_id: str, reviewer: str | None, reason: str | None):
        return self.repo.rollback_candidate(candidate_pack_id, reviewer, reason)

    def ingest_diagnostic(self, payload: dict):
        return self.repo.ingest_diagnostic(payload)

    def list_diagnostics(self):
        return self.repo.list_diagnostics()
