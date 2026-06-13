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
