from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class BehaviorPackCandidate:
    candidate_pack_id: str
    base_pack_id: str
    game_type: str
    version: str
    status: str
    created_from_run_id: str
    created_at: str
    rollback_target: str
    changes: list[dict[str, Any]]
    pack_content: dict[str, Any]

    def with_status(self, status: str) -> BehaviorPackCandidate:
        pack_content = dict(self.pack_content)
        pack_content["status"] = status
        return replace(self, status=status, pack_content=pack_content)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RecommendationEngine:
    def generate_candidate(self, result, base_pack: dict[str, Any]):
        base_pack_id = str(base_pack["pack_id"])
        version = self._next_version(str(base_pack.get("version", "1.0")))
        candidate_pack_id = f"{base_pack_id}_v{version.replace('.', '_')}_candidate"
        fallback_recommendations = [
            "需要人工复核行为包策略"
            for _ in result.issues
        ]
        changes = [
            {"issue": issue, "recommendation": recommendation}
            for issue, recommendation in zip(
                result.issues,
                result.recommendations or fallback_recommendations,
            )
        ]
        if result.recommendations and not changes:
            changes = [
                {"issue": "general_improvement", "recommendation": recommendation}
                for recommendation in result.recommendations
            ]
        pack_content = dict(base_pack)
        pack_content["pack_id"] = candidate_pack_id
        pack_content["version"] = version
        pack_content["status"] = "pending_review"
        pack_content["base_pack_id"] = base_pack_id
        pack_content["rollback_target"] = base_pack_id
        pack_content["learning_changes"] = changes
        pack_content["training_enabled"] = False
        candidate = BehaviorPackCandidate(
            candidate_pack_id=candidate_pack_id,
            base_pack_id=base_pack_id,
            game_type=str(base_pack["game_type"]),
            version=version,
            status="pending_review",
            created_from_run_id=result.run_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            rollback_target=base_pack_id,
            changes=changes,
            pack_content=pack_content,
        )
        recommendation = {
            "run_id": result.run_id,
            "old_behavior_pack_id": result.old_behavior_pack_id,
            "candidate_pack_id": candidate.candidate_pack_id,
            "issues": result.issues,
            "recommendations": result.recommendations,
            "review_status": "pending_review",
            "training_executed": False,
        }
        return candidate, recommendation

    def _next_version(self, version: str) -> str:
        parts = version.split(".")
        try:
            major = int(parts[0])
        except (ValueError, IndexError):
            major = 1
        return f"{major + 1}.0"
