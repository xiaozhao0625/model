from __future__ import annotations

from pathlib import Path

from ai_screenshot_platform.common.behavior.loader import BehaviorPackLoader
from ai_screenshot_platform.common.behavior.mock_runner import MockBehaviorRunner
from ai_screenshot_platform.common.behavior.safety import BehaviorSafetyGate
from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.common.worker.contracts import (
    WorkerCapability,
    WorkerProfile,
    WorkerResult,
    WorkerState,
    WorkerTask,
    WorkerType,
)


class BehaviorWorkerAgent:
    required_capabilities = frozenset(
        {
            WorkerCapability.CAPTURE_HIGH,
            WorkerCapability.BEHAVIOR_PACK,
        }
    )
    allowed_worker_types = frozenset({WorkerType.PC_GAME, WorkerType.MOCK})

    def __init__(self, profile: WorkerProfile) -> None:
        self.profile = profile
        self.safety_gate = BehaviorSafetyGate()

    def execute(self, task: WorkerTask) -> WorkerResult:
        session = self._make_session(task)
        try:
            validation_error = self._validate_task(task)
            if validation_error is not None:
                return self._error_result(session, validation_error, task.behavior_pack_id)

            pack_path = Path(task.behavior_pack_path).resolve()
            behavior_pack = BehaviorPackLoader.load(pack_path)
            blocked_reason = self._blocked_reason(behavior_pack, task)
            if blocked_reason is not None:
                return self._error_result(session, blocked_reason, behavior_pack.pack_id)

            self.profile.state = WorkerState.RUNNING
            self.profile.current_run_id = task.run_id
            session.start()
            run_result = MockBehaviorRunner(
                behavior_pack=behavior_pack,
                session=session,
                safety_gate=self.safety_gate,
            ).run(context=task.context)
            summary = session.generate_summary()
            self.profile.state = WorkerState.STOPPED
            self.profile.current_run_id = None
            return WorkerResult(
                app_id=task.app_id,
                run_id=task.run_id,
                status=run_result.status,
                valid_total=int(summary["valid_total"]),
                fixed_count=int(summary["fixed_count"]),
                low_count=int(summary["low_count"]),
                high_count=int(summary["high_count"]),
                rejected_count=int(summary["rejected_count"]),
                run_dir=session.run_dir,
                summary_path=session.run_dir / "summary.json",
                behavior_pack_id=behavior_pack.pack_id,
                behavior_actions_path=run_result.actions_log_path,
            )
        except Exception as exc:
            self.profile.state = WorkerState.FAILED
            return self._error_result(session, str(exc), task.behavior_pack_id)

    def _validate_task(self, task: WorkerTask) -> str | None:
        if self.profile.worker_type not in self.allowed_worker_types:
            return "worker_type must be pc_game or mock"

        missing = self.required_capabilities - self.profile.capabilities
        if missing:
            return "missing required capabilities: " + ", ".join(
                sorted(capability.value for capability in missing)
            )

        if task.behavior_pack_path is None:
            return "behavior_pack_path is required"

        pack_path = Path(task.behavior_pack_path)
        if not pack_path.exists():
            return f"behavior_pack_path does not exist: {pack_path}"

        return None

    def _blocked_reason(self, behavior_pack, task: WorkerTask) -> str | None:
        for action in behavior_pack.actions:
            decision = self.safety_gate.validate(
                behavior_pack,
                action,
                context=task.context,
            )
            if decision.blocked:
                return decision.reason
        return None

    def _make_session(self, task: WorkerTask) -> LocalRunSession:
        return LocalRunSession(
            RunSessionConfig(
                root_dir=task.root_dir,
                app_id=task.app_id,
                run_id=task.run_id,
                target_min=task.target_min,
                target_max=task.target_max,
            )
        )

    def _error_result(
        self,
        session: LocalRunSession,
        error: str,
        behavior_pack_id: str | None,
    ) -> WorkerResult:
        self.profile.state = WorkerState.FAILED
        self.profile.current_run_id = None
        return WorkerResult(
            app_id=session.config.app_id,
            run_id=session.config.run_id,
            status=session.status
            if session.status != RunStatus.CAPTURE_COMPLETED
            else RunStatus.RUNNING,
            valid_total=0,
            fixed_count=0,
            low_count=0,
            high_count=0,
            rejected_count=0,
            run_dir=session.run_dir,
            summary_path=session.run_dir / "summary.json",
            error=error,
            behavior_pack_id=behavior_pack_id,
            behavior_actions_path=None,
        )
