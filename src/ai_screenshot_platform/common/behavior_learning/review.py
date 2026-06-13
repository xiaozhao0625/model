from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_screenshot_platform.common.behavior_learning.recommendation import (
    BehaviorPackCandidate,
)


@dataclass(frozen=True)
class BehaviorReviewDecision:
    candidate_pack_id: str
    decision: str
    status: str
    reviewer: str
    reason: str
    note: str
    reviewed_at: str
    timestamp: str
    enabled: bool
    rollback_target: str | None = None


class BehaviorReviewManager:
    allowed_decisions = {"approved", "rejected", "rollback"}

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def can_enable(self, candidate: BehaviorPackCandidate) -> bool:
        return candidate.status == "approved"

    def approve_candidate(
        self,
        candidate: BehaviorPackCandidate,
        reviewer: str,
        reason: str | None = None,
        note: str | None = None,
    ) -> BehaviorReviewDecision:
        decision = self._decision(
            candidate.candidate_pack_id,
            "approved",
            reviewer,
            reason or note or "",
            enabled=True,
            rollback_target=candidate.rollback_target,
        )
        self._append_jsonl("review_record.jsonl", asdict(decision))
        return decision

    def reject_candidate(
        self,
        candidate: BehaviorPackCandidate,
        reviewer: str,
        reason: str | None = None,
        note: str | None = None,
    ) -> BehaviorReviewDecision:
        decision = self._decision(
            candidate.candidate_pack_id,
            "rejected",
            reviewer,
            reason or note or "",
            enabled=False,
            rollback_target=candidate.rollback_target,
        )
        self._append_jsonl("review_record.jsonl", asdict(decision))
        return decision

    def rollback_to(
        self,
        candidate_pack_id: str,
        reviewer: str,
        rollback_target: str,
        reason: str | None = None,
        note: str | None = None,
    ) -> BehaviorReviewDecision:
        decision = self._decision(
            candidate_pack_id,
            "rollback",
            reviewer,
            reason or note or "",
            enabled=True,
            rollback_target=rollback_target,
        )
        self._append_jsonl("rollback_record.jsonl", asdict(decision))
        return decision

    def _decision(
        self,
        candidate_pack_id: str,
        decision: str,
        reviewer: str,
        reason: str,
        enabled: bool,
        rollback_target: str | None,
    ) -> BehaviorReviewDecision:
        if decision not in self.allowed_decisions:
            raise ValueError(f"invalid review decision: {decision}")
        if not reviewer:
            raise ValueError("reviewer is required")
        timestamp = datetime.now(timezone.utc).isoformat()
        return BehaviorReviewDecision(
            candidate_pack_id=candidate_pack_id,
            decision=decision,
            status=decision,
            reviewer=reviewer,
            reason=reason,
            note=reason,
            reviewed_at=timestamp,
            timestamp=timestamp,
            enabled=enabled,
            rollback_target=rollback_target,
        )

    def _append_jsonl(self, filename: str, payload: dict) -> None:
        path = self.output_dir / filename
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
