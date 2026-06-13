from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from ai_screenshot_platform.common.behavior.contracts import (
    BehaviorAction,
    BehaviorActionType,
    BehaviorPack,
    BehaviorRunResult,
)
from ai_screenshot_platform.common.behavior.safety import BehaviorSafetyGate
from ai_screenshot_platform.common.domain.buckets import Bucket
from ai_screenshot_platform.common.runtime.run_session import LocalRunSession


class MockBehaviorRunner:
    def __init__(
        self,
        behavior_pack: BehaviorPack,
        session: LocalRunSession,
        safety_gate: BehaviorSafetyGate | None = None,
    ) -> None:
        self.behavior_pack = behavior_pack
        self.session = session
        self.safety_gate = safety_gate or BehaviorSafetyGate()
        self.actions_log_path = self.session.run_dir / "behavior_actions.jsonl"

    def run(self, context: Iterable[Any] | None = None) -> BehaviorRunResult:
        for index, action in enumerate(self.behavior_pack.actions):
            decision = self.safety_gate.validate(self.behavior_pack, action, context)
            if decision.blocked:
                self._log_action(
                    action=action,
                    bucket=action.bucket or self.behavior_pack.capture_bucket,
                    skipped=True,
                    risk_flags=decision.risk_flags,
                    result=decision.action_type.value,
                )
                continue

            bucket = action.bucket or self.behavior_pack.capture_bucket
            self.session.save_image(
                bucket=bucket,
                image_bytes=self._mock_image_bytes(action, index),
            )
            self._log_action(
                action=action,
                bucket=bucket,
                skipped=False,
                risk_flags=decision.risk_flags,
                result="mocked",
            )

        decision = self.session.evaluate_completion()
        if decision.valid_total < self.session.config.target_min:
            self._fill_to_target_min()
            self.session.evaluate_completion()

        summary = self.session.generate_summary()
        return BehaviorRunResult(
            app_id=self.session.config.app_id,
            run_id=self.session.config.run_id,
            behavior_pack_id=self.behavior_pack.pack_id,
            status=self.session.status,
            valid_total=int(summary["valid_total"]),
            fixed_count=int(summary["fixed_count"]),
            low_count=int(summary["low_count"]),
            high_count=int(summary["high_count"]),
            rejected_count=int(summary["rejected_count"]),
            run_dir=self.session.run_dir,
            actions_log_path=self.actions_log_path,
            real_actions_executed=False,
        )

    def _fill_to_target_min(self) -> None:
        summary = self.session.generate_summary()
        valid_total = int(summary["valid_total"])
        for index in range(valid_total, self.session.config.target_min):
            bucket = self.behavior_pack.capture_bucket
            self.session.save_image(
                bucket=bucket,
                image_bytes=(
                    f"{self.behavior_pack.pack_id}:fill:{self.session.config.run_id}:{index}"
                ).encode("utf-8"),
            )

    def _mock_image_bytes(self, action: BehaviorAction, index: int) -> bytes:
        return (
            f"{self.behavior_pack.pack_id}:{self.session.config.run_id}:"
            f"{index}:{action.action_id}:{action.action_type.value}"
        ).encode("utf-8")

    def _log_action(
        self,
        action: BehaviorAction,
        bucket: Bucket,
        skipped: bool,
        risk_flags: list[str],
        result: str,
    ) -> None:
        self.actions_log_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "app_id": self.session.config.app_id,
            "run_id": self.session.config.run_id,
            "behavior_pack_id": self.behavior_pack.pack_id,
            "action_id": action.action_id,
            "action_type": action.action_type.value,
            "bucket": bucket.value,
            "skipped": skipped,
            "risk_flags": risk_flags,
            "result": result,
        }
        with self.actions_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
