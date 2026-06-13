from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ai_screenshot_platform.common.behavior_learning.inputs import (
    BehaviorLearningSnapshot,
)


@dataclass(frozen=True)
class BehaviorMetrics:
    valid_total: int = 0
    fixed_count: int = 0
    low_count: int = 0
    high_count: int = 0
    rejected_count: int = 0
    duplicate_ratio: float = 0.0
    rejected_ratio: float = 0.0
    valid_yield: float = 0.0
    novel_frame_rate: float = 0.0
    action_count: int = 0
    saved_images_per_action: float = 0.0
    manual_seed_count: int = 0
    failed_low_yield: bool = False
    main_bucket_present: bool = False
    action_type_distribution: dict[str, int] = field(default_factory=dict)
    skipped_action_count: int = 0
    risky_action_count: int = 0
    capture_hint_count: int = 0
    saved_after_action: int = 0
    duplicate_after_action: int = 0


@dataclass(frozen=True)
class FpsBehaviorMetrics:
    duplicate_ratio: float
    novel_frame_rate: float
    motion_score: float
    camera_diversity: float
    stuck_ratio: float
    death_loop_ratio: float
    combat_effectiveness: float
    respawn_recovery_rate: float
    high_yield_rate: float


@dataclass(frozen=True)
class MobaBehaviorMetrics:
    lane_coverage: float
    shop_coverage: float
    scoreboard_coverage: float
    skill_usage_coverage: float
    combat_scene_count: int
    teamfight_scene_count: int
    camera_lost_ratio: float
    base_stuck_ratio: float
    high_yield_rate: float
    low_yield_rate: float


class BehaviorMetricsCalculator:
    def calculate(self, snapshot: BehaviorLearningSnapshot) -> BehaviorMetrics:
        summary = snapshot.summary
        valid_total = int(summary.get("valid_total", 0))
        rejected_count = int(summary.get("rejected_count", 0))
        total_seen = max(valid_total + rejected_count, 1)
        duplicate_count = self._duplicate_count(snapshot)
        action_count = len(snapshot.behavior_actions)
        event_names = [str(event.get("event", "")) for event in snapshot.run_events]
        distribution = Counter(
            str(action.get("action_type", "unknown"))
            for action in snapshot.behavior_actions
        )
        risky_action_count = sum(
            1 for action in snapshot.behavior_actions if action.get("risk_flags")
        )
        capture_hint_count = distribution.get("capture_hint", 0)
        skipped_action_count = sum(
            1 for action in snapshot.behavior_actions if bool(action.get("skipped"))
        )
        manual_seed_count = event_names.count("manual_seed_requested") + len(
            snapshot.manual_seed_events or []
        )
        return BehaviorMetrics(
            valid_total=valid_total,
            fixed_count=int(summary.get("fixed_count", 0)),
            low_count=int(summary.get("low_count", 0)),
            high_count=int(summary.get("high_count", 0)),
            rejected_count=rejected_count,
            duplicate_ratio=duplicate_count / max(valid_total, 1),
            rejected_ratio=rejected_count / total_seen,
            valid_yield=valid_total / total_seen,
            novel_frame_rate=max(valid_total - duplicate_count, 0) / max(valid_total, 1),
            action_count=action_count,
            saved_images_per_action=valid_total / max(action_count, 1),
            manual_seed_count=manual_seed_count,
            failed_low_yield="failed_low_yield" in event_names,
            main_bucket_present=bool(summary.get("low_count", 0) or summary.get("high_count", 0)),
            action_type_distribution=dict(distribution),
            skipped_action_count=skipped_action_count,
            risky_action_count=risky_action_count,
            capture_hint_count=capture_hint_count,
            saved_after_action=valid_total,
            duplicate_after_action=duplicate_count,
        )

    def _duplicate_count(self, snapshot: BehaviorLearningSnapshot) -> int:
        duplicate_meta = sum(
            1
            for row in snapshot.meta_rows
            if row.get("reject_reason") == "duplicate_content_hash"
        )
        duplicate_logs = sum(
            1
            for event in snapshot.run_events
            if event.get("event") == "duplicate_rejected"
        )
        return max(duplicate_meta, duplicate_logs)
