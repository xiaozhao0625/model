from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkerAgentConfig:
    worker_id: str
    worker_type: str
    machine_name: str
    capabilities: list[str] = field(default_factory=list)
    master_url: str = "http://127.0.0.1:8000"
    data_root: str | Path = "runs/worker_agent"
    heartbeat_interval_sec: int = 5
    execution_mode: str = "mock"


class WorkerAgentConfigLoader:
    @classmethod
    def load_many(cls, path: str | Path) -> list[WorkerAgentConfig]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        workers = payload.get("workers")
        if not isinstance(workers, list) or not workers:
            raise ValueError("worker config must contain a non-empty workers list")
        return [cls.from_dict(item) for item in workers]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorkerAgentConfig:
        required = ["worker_id", "worker_type", "machine_name", "execution_mode"]
        missing = [key for key in required if key not in payload]
        if missing:
            raise ValueError("missing worker config fields: " + ", ".join(missing))
        return WorkerAgentConfig(
            worker_id=str(payload["worker_id"]),
            worker_type=str(payload["worker_type"]),
            machine_name=str(payload["machine_name"]),
            capabilities=[str(item) for item in payload.get("capabilities", [])],
            master_url=str(payload.get("master_url", "http://127.0.0.1:8000")),
            data_root=payload.get("data_root", "runs/worker_agent"),
            heartbeat_interval_sec=int(payload.get("heartbeat_interval_sec", 5)),
            execution_mode=str(payload["execution_mode"]),
        )
