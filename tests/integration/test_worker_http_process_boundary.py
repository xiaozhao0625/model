from __future__ import annotations

import socket
import threading
import time
import warnings
from pathlib import Path

import uvicorn

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

from fastapi.testclient import TestClient

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings
from ai_screenshot_platform.worker_agent.config import WorkerAgentConfigLoader
from ai_screenshot_platform.worker_agent.master_client import MasterApiClient
from ai_screenshot_platform.worker_agent.runtime import WorkerRuntime


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class UvicornThread:
    def __init__(self, app, port: int) -> None:
        self.config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="critical",
        )
        self.server = uvicorn.Server(self.config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 5
        while not self.server.started:
            if time.time() > deadline:
                raise RuntimeError("uvicorn test server did not start")
            time.sleep(0.05)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.should_exit = True
        self.thread.join(timeout=5)


def unwrap(response):
    payload = response.json()
    assert payload["code"] == 0
    return payload["data"]


def make_app(tmp_path: Path):
    settings = MasterSettings(
        database_url=f"sqlite:///{tmp_path / 'master.db'}",
        redis_url="memory://",
        env="test",
        data_root=tmp_path / "master",
    )
    return create_app(settings)


def test_worker_http_once_mode_claims_executes_and_reports(tmp_path):
    app = make_app(tmp_path)
    with TestClient(app) as setup_client:
        unwrap(
            setup_client.post(
                "/api/apps",
                json={
                    "app_id": "http_app",
                    "name": "HTTP App",
                    "type": "pc_app",
                    "platform": "windows",
                },
            )
        )
        unwrap(
            setup_client.post(
                "/api/runs",
                json={
                    "run_id": "http_run",
                    "app_id": "http_app",
                    "target_min": 3,
                    "target_max": 5000,
                },
            )
        )

    port = free_port()
    master_url = f"http://127.0.0.1:{port}"
    with UvicornThread(app, port):
        runtime = WorkerRuntime(
            config=WorkerAgentConfigLoader.from_dict(
                {
                    "worker_id": "worker_http_mock",
                    "worker_type": "mock",
                    "machine_name": "single-node-http",
                    "capabilities": ["capture_low"],
                    "master_url": master_url,
                    "data_root": str(tmp_path / "worker"),
                    "heartbeat_interval_sec": 1,
                    "execution_mode": "mock",
                }
            ),
            client=MasterApiClient(master_url),
        )

        result = runtime.start_once()
        client = MasterApiClient(master_url)
        no_task = client.claim_task("worker_http_mock")

    with TestClient(app) as verify_client:
        final_run = unwrap(verify_client.get("/api/runs/http_run"))

    assert result["claim_status"] == "claimed"
    assert result["execution_status"] == RunStatus.CAPTURE_COMPLETED.value
    assert final_run["status"] == RunStatus.CAPTURE_COMPLETED.value
    assert final_run["valid_total"] == 3
    assert final_run["status"] != RunStatus.UPLOAD_PENDING.value
    assert final_run["status"] != RunStatus.COMPLETED.value
    assert no_task["status"] == "no_task"
