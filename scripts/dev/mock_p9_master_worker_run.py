from __future__ import annotations

import json
import shutil
import sys
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from ai_screenshot_platform.common.domain.run_status import RunStatus  # noqa: E402
from ai_screenshot_platform.master.api.app import create_app  # noqa: E402
from ai_screenshot_platform.master.core.config import MasterSettings  # noqa: E402
from ai_screenshot_platform.worker_agent.config import (  # noqa: E402
    WorkerAgentConfigLoader,
)
from ai_screenshot_platform.worker_agent.master_client import (  # noqa: E402
    MasterApiClient,
)
from ai_screenshot_platform.worker_agent.runtime import WorkerRuntime  # noqa: E402


def unwrap(response):
    payload = response.json()
    if payload["code"] != 0:
        raise RuntimeError(payload)
    return payload["data"]


def run(root: Path) -> dict[str, object]:
    root = root.resolve()
    allowed_root = (REPO_ROOT / "runs").resolve()
    if root.exists():
        if allowed_root not in root.parents:
            raise ValueError(f"refusing to clean path outside runs/: {root}")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    settings = MasterSettings(
        database_url=f"sqlite:///{root / 'master' / 'master.db'}",
        redis_url="memory://",
        env="dev",
        data_root=root / "master",
    )

    with TestClient(create_app(settings)) as api:
        unwrap(
            api.post(
                "/api/apps",
                json={
                    "app_id": "demo_app",
                    "name": "Demo App",
                    "type": "pc_app",
                    "platform": "windows",
                },
            )
        )
        unwrap(
            api.post(
                "/api/runs",
                json={
                    "run_id": "demo_p9_run",
                    "app_id": "demo_app",
                    "target_min": 3,
                    "target_max": 5000,
                },
            )
        )
        config = WorkerAgentConfigLoader.from_dict(
            {
                "worker_id": "worker_p9_mock",
                "worker_type": "mock",
                "machine_name": "single-node-dev",
                "capabilities": ["capture_low"],
                "master_url": "testserver",
                "data_root": str(root / "worker"),
                "heartbeat_interval_sec": 1,
                "execution_mode": "mock",
            }
        )
        runtime_result = WorkerRuntime(
            config=config,
            client=MasterApiClient("testserver", test_client=api),
        ).start_once()
        final_run = unwrap(api.get("/api/runs/demo_p9_run"))

    run_dir = Path(str(runtime_result["run_dir"]))
    return {
        "app_id": final_run["app_id"],
        "run_id": final_run["run_id"],
        "worker_id": runtime_result["worker_id"],
        "claim_status": runtime_result["claim_status"],
        "execution_status": runtime_result["execution_status"],
        "final_run_status": final_run["status"],
        "valid_total": final_run["valid_total"],
        "fixed_count": final_run["fixed_count"],
        "low_count": final_run["low_count"],
        "high_count": final_run["high_count"],
        "rejected_count": final_run["rejected_count"],
        "summary_path": runtime_result["summary_path"],
        "run_log_path": runtime_result["run_log_path"],
        "upload_manifest_absent": not (run_dir / "upload_manifest.json").exists(),
        "completed_absent": final_run["status"] != RunStatus.COMPLETED.value,
    }


def main() -> None:
    print(
        json.dumps(
            run(REPO_ROOT / "runs" / "dev_p9_smoke"),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
