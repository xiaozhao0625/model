from __future__ import annotations

from ai_screenshot_platform.common.behavior_learning.fps_analyzer import BehaviorAnalysis
from ai_screenshot_platform.common.behavior_learning.metrics import BehaviorMetrics


class MobaBehaviorAnalyzer:
    def __init__(
        self,
        base_stuck_threshold: float = 0.2,
        camera_lost_threshold: float = 0.2,
    ) -> None:
        self.base_stuck_threshold = base_stuck_threshold
        self.camera_lost_threshold = camera_lost_threshold

    def analyze(self, metrics: BehaviorMetrics) -> BehaviorAnalysis:
        issues: list[str] = []
        recommendations: list[str] = []
        distribution = metrics.action_type_distribution
        base_stuck_ratio = metrics.skipped_action_count / max(metrics.action_count, 1)
        camera_lost_ratio = 1.0 if distribution.get("camera", 0) == 0 else 0.0
        if base_stuck_ratio >= self.base_stuck_threshold:
            issues.append("base_stuck_detected")
            recommendations.append("增加出门路线点，按 Space 回英雄")
        if distribution.get("move", 0) < 2:
            issues.append("lane_coverage_low")
            recommendations.append("增加中路线点、河道点和野区点")
        if distribution.get("ui", 0) > distribution.get("move", 0):
            issues.append("shop_stuck_high")
            recommendations.append("限制商店打开时间并增加 return_to_lane")
        if distribution.get("combat", 0) == 0:
            issues.append("skill_usage_low")
            recommendations.append("增加技能升级动作和 Q/W/E/R 使用概率")
        if distribution.get("combat", 0) < 2:
            issues.append("teamfight_scene_low")
            recommendations.append("增加观察队友和多人聚集区域镜头移动")
        if camera_lost_ratio >= self.camera_lost_threshold:
            issues.append("camera_lost_high")
            recommendations.append("增加 press_space_to_center_hero 和 camera_follow_hero")
        return BehaviorAnalysis(
            issues=issues,
            recommendations=list(dict.fromkeys(recommendations)),
            details={
                "base_stuck_ratio": base_stuck_ratio,
                "camera_lost_ratio": camera_lost_ratio,
                "high_yield_rate": metrics.high_count / max(metrics.valid_total, 1),
                "low_yield_rate": metrics.low_count / max(metrics.valid_total, 1),
            },
        )
