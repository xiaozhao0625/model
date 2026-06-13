from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.worker.contracts import (
    WorkerCapability,
    WorkerProfile,
    WorkerTask,
    WorkerType,
)
from ai_screenshot_platform.worker_agent.config import WorkerAgentConfig
from ai_screenshot_platform.worker_agent.executors import ExecutorResolver
from ai_screenshot_platform.worker_agent.master_client import MasterApiClient


class WorkerRuntime:
    def __init__(
        self,
        config: WorkerAgentConfig,
        client: MasterApiClient,
        executor_resolver: ExecutorResolver | None = None,
    ) -> None:
        self.config = config
        self.client = client
        self.executor_resolver = executor_resolver or ExecutorResolver()

    def start_once(self) -> dict[str, Any]:
        self.client.register_worker(
            worker_id=self.config.worker_id,
            worker_type=self.config.worker_type,
            machine_name=self.config.machine_name,
            capabilities=self.config.capabilities,
        )
        self.client.send_heartbeat(self.config.worker_id)
        claim = self.client.claim_task(self.config.worker_id)
        if claim["status"] != "claimed" or claim.get("task") is None:
            return {
                "worker_id": self.config.worker_id,
                "claim_status": claim["status"],
                "execution_status": None,
                "report_status": None,
            }

        task = self._task_from_claim(claim["task"])
        result = self.executor_resolver.execute(
            self.config.execution_mode,
            task,
            profile=self._profile(),
        )
        report = self.client.report_result(
            worker_id=self.config.worker_id,
            run_id=task.run_id,
            payload=self.executor_resolver.result_to_payload(result),
        )
        return {
            "worker_id": self.config.worker_id,
            "run_id": task.run_id,
            "claim_status": claim["status"],
            "execution_status": result.status.value,
            "report_status": report["run"]["status"],
            "valid_total": result.valid_total,
            "fixed_count": result.fixed_count,
            "low_count": result.low_count,
            "high_count": result.high_count,
            "rejected_count": result.rejected_count,
            "run_dir": str(result.run_dir),
            "summary_path": str(result.summary_path),
            "run_log_path": str(Path(result.run_dir) / "run.log"),
        }

    def _task_from_claim(self, payload: dict[str, Any]) -> WorkerTask:
        return WorkerTask(
            app_id=str(payload["app_id"]),
            run_id=str(payload["run_id"]),
            app_type=str(payload["app_type"]),
            platform=str(payload["platform"]),
            target_min=int(payload["target_min"]),
            target_max=int(payload["target_max"]),
            bucket=str(payload["bucket"]),
            root_dir=self.config.data_root,
            behavior_pack_path=payload.get("behavior_pack_path"),
            behavior_pack_id=payload.get("behavior_pack_id"),
            context=list(payload.get("context") or []),
        )

    def _profile(self) -> WorkerProfile:
        capabilities = {
            WorkerCapability(item)
            for item in self.config.capabilities
            if item in {capability.value for capability in WorkerCapability}
        }
        return WorkerProfile(
            worker_id=self.config.worker_id,
            machine_name=self.config.machine_name,
            worker_type=WorkerType(self.config.worker_type),
            gpu_name=None,
            capabilities=capabilities,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self.config)
