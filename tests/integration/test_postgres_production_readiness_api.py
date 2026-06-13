from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings


def postgres_url() -> str | None:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if url and url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
        return url
    return None


@pytest.mark.skipif(postgres_url() is None, reason="PostgreSQL URL is not configured")
def test_postgres_production_readiness_api_roundtrip(tmp_path: Path):
    suffix = uuid4().hex[:8]
    settings = MasterSettings(
        database_url=postgres_url() or "",
        redis_url="memory://",
        env="test",
        data_root=tmp_path,
    )
    with TestClient(create_app(settings)) as client:
        run_id = f"pg_quality_{suffix}"
        candidate_id = f"pg_candidate_{suffix}"

        assert client.post(
            "/api/quality-reports/ingest",
            json={"app_id": "pg_app", "run_id": run_id, "total_images": 1, "accepted_count": 1, "rejected_count": 0},
        ).status_code == 200
        assert client.get(f"/api/quality-reports/{run_id}").status_code == 200

        assert client.post(
            "/api/behavior-candidates/ingest",
            json={
                "candidate_pack_id": candidate_id,
                "base_pack_id": "base",
                "game_type": "fps",
                "version": "2.0",
                "rollback_target": "base",
                "created_from_run_id": run_id,
            },
        ).status_code == 200
        assert client.post(f"/api/behavior-candidates/{candidate_id}/approve", json={"reviewer": "qa"}).status_code == 200
