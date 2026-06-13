from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.coverage.retry_policy import (  # noqa: E402
    RetryPolicy,
    RetryState,
)
from ai_screenshot_platform.common.domain.buckets import Bucket  # noqa: E402
from ai_screenshot_platform.common.domain.run_status import RunStatus  # noqa: E402
from ai_screenshot_platform.common.runtime.run_session import (  # noqa: E402
    LocalRunSession,
    RunSessionConfig,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local mock P5 recovery flow.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--target-min", type=int, default=1000)
    return parser.parse_args()


def create_session(root: str | Path, run_id: str, target_min: int) -> LocalRunSession:
    return LocalRunSession(
        RunSessionConfig(
            root_dir=root,
            app_id="demo_app",
            run_id=run_id,
            target_min=target_min,
        )
    )


def save_low_images(session: LocalRunSession, count: int, prefix: str) -> None:
    for index in range(count):
        session.save_image(Bucket.LOW, f"{prefix}-low-{index}".encode("utf-8"))


def exhausted_retry_decision(session: LocalRunSession) -> Any:
    return RetryPolicy.evaluate(
        counts=session.store.capture_counts(),
        retry_state=RetryState(retry_round=2, max_auto_retries=2),
        target_min=session.config.target_min,
        target_max=session.config.target_max,
        fixed_cap=session.config.fixed_cap,
    )


def run_manual_seed_success(root: str | Path, target_min: int) -> dict[str, Any]:
    session = create_session(root, "manual_seed_success", target_min)
    session.start()
    save_low_images(session, max(target_min - 1, 0), "manual-seed-pre")

    decision = exhausted_retry_decision(session)
    session.request_manual_seed(
        reason=decision.reason.value,
        retry_round=decision.current_retry_round,
        operator="dry-run",
        note="manual seed requested",
    )
    session.resume_after_manual_seed(
        reason="manual_seed_added",
        retry_round=decision.current_retry_round,
        operator="dry-run",
        note="manual seed completed",
    )

    while session.store.capture_counts().valid_total < target_min:
        next_index = session.store.capture_counts().valid_total
        session.save_image(Bucket.LOW, f"manual-seed-post-{next_index}".encode("utf-8"))

    session.evaluate_completion()
    summary = session.generate_summary()
    return scenario_result(session, summary)


def run_failed_low_yield(root: str | Path, target_min: int) -> dict[str, Any]:
    session = create_session(root, "failed_low_yield", target_min)
    session.start()
    save_low_images(session, max(target_min - 1, 0), "failed-low-yield-pre")

    decision = exhausted_retry_decision(session)
    session.request_manual_seed(
        reason=decision.reason.value,
        retry_round=decision.current_retry_round,
        operator="dry-run",
        note="manual seed requested",
    )
    session.resume_after_manual_seed(
        reason="manual_seed_added",
        retry_round=decision.current_retry_round,
        operator="dry-run",
        note="manual seed completed",
    )
    summary = session.generate_summary()
    session.mark_failed_low_yield(
        reason="still_below_target",
        retry_round=decision.current_retry_round,
        operator="dry-run",
        note="stop after manual seed",
    )
    return scenario_result(session, summary)


def scenario_result(
    session: LocalRunSession,
    summary: dict[str, int | str],
) -> dict[str, Any]:
    return {
        "final_status": session.status.value,
        "valid_total": summary["valid_total"],
        "manual_seed_record_path": str(session.manual_seed_record_path),
        "run_log_path": str(session.run_log_path),
        "upload_manifest_absent": not session.upload_manifest_path.exists(),
        "completed_absent": session.status != RunStatus.COMPLETED,
    }


def run_mock(args: argparse.Namespace) -> dict[str, Any]:
    scenario_results = {
        "manual_seed_success": run_manual_seed_success(args.root, args.target_min),
        "failed_low_yield": run_failed_low_yield(args.root, args.target_min),
    }
    scenarios = list(scenario_results)
    return {
        "scenarios": scenarios,
        "final_status_by_scenario": {
            scenario: result["final_status"]
            for scenario, result in scenario_results.items()
        },
        "valid_total_by_scenario": {
            scenario: result["valid_total"]
            for scenario, result in scenario_results.items()
        },
        "manual_seed_record_path": {
            scenario: result["manual_seed_record_path"]
            for scenario, result in scenario_results.items()
        },
        "run_log_path": {
            scenario: result["run_log_path"]
            for scenario, result in scenario_results.items()
        },
        "upload_manifest_absent": {
            scenario: result["upload_manifest_absent"]
            for scenario, result in scenario_results.items()
        },
        "completed_absent": {
            scenario: result["completed_absent"]
            for scenario, result in scenario_results.items()
        },
    }


def main() -> None:
    print(json.dumps(run_mock(parse_args()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
