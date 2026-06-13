from __future__ import annotations

import json
from typing import Any
from urllib import request


class MasterApiClient:
    def __init__(self, master_url: str, test_client: Any | None = None) -> None:
        self.master_url = master_url.rstrip("/")
        self.test_client = test_client

    def register_worker(
        self,
        worker_id: str,
        worker_type: str,
        machine_name: str,
        capabilities: list[str],
    ) -> dict[str, Any]:
        return self._post(
            "/api/workers/register",
            {
                "worker_id": worker_id,
                "type": worker_type,
                "machine_name": machine_name,
                "capabilities": capabilities,
            },
        )

    def send_heartbeat(self, worker_id: str) -> dict[str, Any]:
        return self._post(f"/api/workers/{worker_id}/heartbeat", {})

    def claim_task(self, worker_id: str) -> dict[str, Any]:
        return self._post(f"/api/workers/{worker_id}/claim", {})

    def report_result(
        self,
        worker_id: str,
        run_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._post(f"/api/workers/{worker_id}/runs/{run_id}/report", payload)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.test_client is not None:
            response = self.test_client.post(path, json=payload)
            return self._unwrap_response(response.status_code, response.json())

        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.master_url + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return self._unwrap_response(response.status, data)

    def _unwrap_response(self, status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
        if status_code >= 400:
            raise ValueError(payload.get("message") or payload.get("error") or payload)
        if payload.get("code") != 0:
            raise ValueError(payload.get("message") or payload)
        return payload["data"]
