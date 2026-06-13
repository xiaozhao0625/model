from __future__ import annotations

from dataclasses import dataclass

from ai_screenshot_platform.common.behavior_learning.metrics import BehaviorMetrics


@dataclass(frozen=True)
class BehaviorAnalysis:
    issues: list[str]
    recommendations: list[str]
    details: dict[str, float | int | bool]


class FpsBehaviorAnalyzer:
    def __init__(
        self,
        duplicate_threshold: float = 0.3,
        stuck_threshold: float = 0.15,
        death_loop_threshold: float = 0.2,
        high_yield_threshold: float = 0.2,
    ) -> None:
        self.duplicate_threshold = duplicate_threshold
        self.stuck_threshold = stuck_threshold
        self.death_loop_threshold = death_loop_threshold
        self.high_yield_threshold = high_yield_threshold

    def analyze(self, metrics: BehaviorMetrics) -> BehaviorAnalysis:
        issues: list[str] = []
        recommendations: list[str] = []
        high_yield_rate = metrics.high_count / max(metrics.valid_total, 1)
        stuck_ratio = metrics.skipped_action_count / max(metrics.action_count, 1)
        death_loop_ratio = 1.0 if metrics.failed_low_yield else 0.0
        if metrics.duplicate_ratio > self.duplicate_threshold:
            issues.append("duplicate_ratio_high")
            recommendations.extend(
                [
                    "增加转向幅度",
                    "缩短直线前进时间",
                    "增加左右横移和镜头上下变化",
                ]
            )
        if high_yield_rate < self.high_yield_threshold:
            issues.append("high_yield_low")
            recommendations.append("增加 combat / camera / movement capture_hint")
        if stuck_ratio > self.stuck_threshold:
            issues.append("stuck_ratio_high")
            recommendations.append("增加 recover_if_stuck、后退和随机转向动作")
        if death_loop_ratio > self.death_loop_threshold:
            issues.append("death_loop_high")
            recommendations.append("增加 respawn 检测，减少无脑冲锋")
        if metrics.action_type_distribution.get("combat", 0) == 0:
            issues.append("combat_effectiveness_low")
            recommendations.append("增加 fire_burst、reload 和 camera scan")
        return BehaviorAnalysis(
            issues=issues,
            recommendations=list(dict.fromkeys(recommendations)),
            details={
                "high_yield_rate": high_yield_rate,
                "stuck_ratio": stuck_ratio,
                "death_loop_ratio": death_loop_ratio,
                "combat_effectiveness": metrics.action_type_distribution.get("combat", 0),
            },
        )
