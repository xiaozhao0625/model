from __future__ import annotations

from ai_screenshot_platform.common.behavior_learning.recommendation import (
    BehaviorPackCandidate,
    RecommendationEngine,
)


class BehaviorPackVersioning:
    def get_next_version(self, base_pack_id: str, current_version: str = "1.0") -> str:
        return RecommendationEngine()._next_version(current_version)

    def create_candidate(self, base_pack: dict, changes: list[dict]) -> BehaviorPackCandidate:
        class Result:
            run_id = "manual"
            old_behavior_pack_id = base_pack["pack_id"]
            issues = [str(change.get("issue", "manual_change")) for change in changes]
            recommendations = [
                str(change.get("recommendation", "manual recommendation"))
                for change in changes
            ]

        candidate, _ = RecommendationEngine().generate_candidate(Result(), base_pack)
        return candidate

    def mark_pending_review(self, candidate: BehaviorPackCandidate) -> BehaviorPackCandidate:
        return candidate.with_status("pending_review")

    def mark_approved(self, candidate: BehaviorPackCandidate) -> BehaviorPackCandidate:
        return candidate.with_status("approved")

    def mark_rejected(self, candidate: BehaviorPackCandidate) -> BehaviorPackCandidate:
        return candidate.with_status("rejected")

    def rollback(
        self,
        candidate: BehaviorPackCandidate,
        target: str,
    ) -> BehaviorPackCandidate:
        return candidate.with_status("rolled_back")
