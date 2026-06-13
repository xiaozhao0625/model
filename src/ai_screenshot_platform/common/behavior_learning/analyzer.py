from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.behavior_learning.fps_analyzer import (
    BehaviorAnalysis,
    FpsBehaviorAnalyzer,
)
from ai_screenshot_platform.common.behavior_learning.inputs import (
    BehaviorLearningInput,
    BehaviorLearningInputReader,
)
from ai_screenshot_platform.common.behavior_learning.metrics import (
    BehaviorMetrics,
    BehaviorMetricsCalculator,
)
from ai_screenshot_platform.common.behavior_learning.moba_analyzer import (
    MobaBehaviorAnalyzer,
)
from ai_screenshot_platform.common.behavior_learning.output_store import (
    BehaviorLearningOutputStore,
)
from ai_screenshot_platform.common.behavior_learning.recommendation import (
    BehaviorPackCandidate,
    RecommendationEngine,
)


@dataclass(frozen=True)
class BehaviorLearningResult:
    run_id: str
    game_type: str
    old_behavior_pack_id: str
    metrics: BehaviorMetrics
    issues: list[str]
    recommendations: list[str]
    should_generate_candidate: bool
    candidate_pack_id: str | None
    review_status: str


@dataclass(frozen=True)
class BehaviorLearningOutput:
    output_dir: Path
    metrics_path: Path
    analysis_path: Path
    recommendation_path: Path
    candidate_pack_path: Path
    result: BehaviorLearningResult
    candidate: BehaviorPackCandidate
    training_executed: bool


class BehaviorLearningEngine:
    def __init__(
        self,
        output_root: str | Path,
        base_pack_path: str | Path,
    ) -> None:
        self.output_store = BehaviorLearningOutputStore(output_root)
        self.base_pack_path = Path(base_pack_path)

    def run(self, learning_input: BehaviorLearningInput) -> BehaviorLearningOutput:
        snapshot = BehaviorLearningInputReader(learning_input).read()
        metrics = BehaviorMetricsCalculator().calculate(snapshot)
        analysis = self._analyze(learning_input.game_type, metrics)
        result = BehaviorLearningResult(
            run_id=learning_input.run_id,
            game_type=learning_input.game_type,
            old_behavior_pack_id=learning_input.behavior_pack_id,
            metrics=metrics,
            issues=analysis.issues,
            recommendations=analysis.recommendations,
            should_generate_candidate=True,
            candidate_pack_id=None,
            review_status="pending_review",
        )
        base_pack = json.loads(self.base_pack_path.read_text(encoding="utf-8"))
        candidate, recommendation = RecommendationEngine().generate_candidate(
            result,
            base_pack,
        )
        output_dir = self.output_store.run_output_dir(
            learning_input.app_id,
            learning_input.run_id,
        )
        metrics_path = self.output_store.write_json(output_dir / "metrics.json", metrics)
        analysis_path = self.output_store.write_json(
            output_dir / "analysis.json",
            {
                "issues": analysis.issues,
                "recommendations": analysis.recommendations,
                "details": analysis.details,
            },
        )
        recommendation_path = self.output_store.write_json(
            output_dir / "recommendation.json",
            recommendation,
        )
        candidate_pack_path = self.output_store.write_json(
            output_dir / "candidate_pack.json",
            candidate.pack_content,
        )
        return BehaviorLearningOutput(
            output_dir=output_dir,
            metrics_path=metrics_path,
            analysis_path=analysis_path,
            recommendation_path=recommendation_path,
            candidate_pack_path=candidate_pack_path,
            result=result,
            candidate=candidate,
            training_executed=False,
        )

    def _analyze(self, game_type: str, metrics: BehaviorMetrics) -> BehaviorAnalysis:
        if game_type == "moba":
            return MobaBehaviorAnalyzer().analyze(metrics)
        return FpsBehaviorAnalyzer().analyze(metrics)
