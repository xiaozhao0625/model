from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings


def postgres_url() -> str | None:
    url = (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or _read_env_file_value("DATABASE_URL")
    )
    if url and url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
        return url
    return None


def _read_env_file_value(name: str) -> str | None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")
    return None


def data(response):
    payload = response.json()
    assert payload["code"] == 0
    return payload["data"]


def _cleanup_postgres_test_data(connection, run_id: str, suffix: str) -> None:
    candidate_prefix = f"test_pg_candidate_{suffix}"
    source_path = f"test_pg:{suffix}"
    worker_id = f"test_pg_worker_{suffix}"
    machine_name = f"test_pg_machine_{suffix}"
    connection.execute("DELETE FROM quality_report_items WHERE run_id = ?", (run_id,))
    connection.execute("DELETE FROM quality_reports WHERE run_id = ?", (run_id,))
    connection.execute("DELETE FROM ocr_risk_hits WHERE run_id = ?", (run_id,))
    connection.execute("DELETE FROM ocr_reports WHERE run_id = ?", (run_id,))
    connection.execute(
        "DELETE FROM behavior_candidate_reviews WHERE candidate_pack_id LIKE ?",
        (f"{candidate_prefix}%",),
    )
    connection.execute(
        "DELETE FROM behavior_candidate_rollbacks WHERE candidate_pack_id LIKE ?",
        (f"{candidate_prefix}%",),
    )
    connection.execute(
        "DELETE FROM behavior_candidates WHERE candidate_pack_id LIKE ?",
        (f"{candidate_prefix}%",),
    )
    connection.execute(
        "DELETE FROM android_runtime_snapshots WHERE worker_id = ? OR source_path = ?",
        (worker_id, source_path),
    )
    connection.execute(
        "DELETE FROM tool_health_snapshots WHERE worker_id = ? OR machine_name = ? OR source_path = ?",
        (worker_id, machine_name, source_path),
    )
    connection.execute(
        "DELETE FROM deployment_diagnostics WHERE source_path = ?",
        (source_path,),
    )
    connection.commit()


def test_postgres_production_readiness_api_roundtrip(tmp_path: Path):
    url = postgres_url()
    if url is None:
        pytest.skip("PostgreSQL URL is not configured")

    suffix = uuid4().hex[:10]
    run_id = f"test_pg_run_{suffix}"
    approved_candidate_id = f"test_pg_candidate_approved_{suffix}"
    rejected_candidate_id = f"test_pg_candidate_rejected_{suffix}"
    worker_id = f"test_pg_worker_{suffix}"
    machine_name = f"test_pg_machine_{suffix}"
    source_path = f"test_pg:{suffix}"
    settings = MasterSettings(
        database_url=url,
        redis_url="memory://",
        env="test",
        data_root=tmp_path,
    )
    with TestClient(create_app(settings)) as client:
        database = client.app.state.database
        assert database is not None
        try:
            quality_report = data(
                client.post(
                    "/api/quality-reports/ingest",
                    json={
                        "app_id": "test_pg_app",
                        "run_id": run_id,
                        "total_images": 12,
                        "accepted_count": 10,
                        "rejected_count": 2,
                        "quality_pass_rate": 0.8333,
                        "browser_chrome_count": 1,
                        "taskbar_count": 1,
                        "ocr_risk_hit_count": 1,
                        "reject_reason_distribution": {
                            "browser_chrome_visible": 1,
                            "ocr_risk_detected": 1,
                        },
                        "source_path": source_path,
                    },
                )
            )
            quality_list = data(client.get("/api/quality-reports"))
            quality_detail = data(client.get(f"/api/quality-reports/{run_id}"))
            assert quality_report["run_id"] == run_id
            assert any(item["run_id"] == run_id for item in quality_list)
            assert quality_detail["accepted_count"] == 10

            ocr_report = data(
                client.post(
                    "/api/ocr/reports/ingest",
                    json={
                        "app_id": "test_pg_app",
                        "run_id": run_id,
                        "provider": "mock",
                        "available": True,
                        "status": "available",
                        "risk_hits": ["payment"],
                        "scene_hints": ["shop", "checkout"],
                        "paddleocr_optional_status": "unavailable",
                        "easyocr_optional_status": "unavailable",
                        "source_path": source_path,
                    },
                )
            )
            ocr_list = data(client.get("/api/ocr/reports"))
            ocr_detail = data(client.get(f"/api/ocr/reports/{run_id}"))
            assert ocr_report["risk_hits"] == ["payment"]
            assert any(item["run_id"] == run_id for item in ocr_list)
            assert ocr_detail["scene_hints"] == ["shop", "checkout"]

            tool_health = data(
                client.post(
                    "/api/tool-health/ingest",
                    json={
                        "machine_name": machine_name,
                        "worker_id": worker_id,
                        "worker_type": "android",
                        "status": "available",
                        "tools": {"ADB": "available", "Playwright": "skipped"},
                        "master_ready": {"status": "available"},
                        "worker_ready": {"status": "available"},
                        "android": {
                            "profile_id": f"test_pg_android_{suffix}",
                            "adb_available": True,
                            "devices": ["emulator-test"],
                            "selected_device": "emulator-test",
                            "screencap_status": "available",
                            "ui_dump_status": "available",
                            "ocr_fallback_status": "skipped",
                            "input_status": "disabled",
                        },
                        "source_path": source_path,
                    },
                )
            )
            tool_health_detail = data(client.get("/api/tool-health"))
            assert tool_health["tools"]["ADB"] == "available"
            assert tool_health_detail["android"]["adb_available"] is True

            approved_candidate = data(
                client.post(
                    "/api/behavior-candidates/ingest",
                    json={
                        "candidate_pack_id": approved_candidate_id,
                        "base_pack_id": "base_pack",
                        "game_type": "fps",
                        "version": "2.0",
                        "rollback_target": "base_pack",
                        "created_from_run_id": run_id,
                        "issues": ["low_variety"],
                        "recommendations": ["increase_camera_sweep"],
                        "source_path": source_path,
                    },
                )
            )
            rejected_candidate = data(
                client.post(
                    "/api/behavior-candidates/ingest",
                    json={
                        "candidate_pack_id": rejected_candidate_id,
                        "base_pack_id": "base_pack",
                        "game_type": "moba",
                        "version": "2.0",
                        "rollback_target": "base_pack",
                        "created_from_run_id": run_id,
                        "source_path": source_path,
                    },
                )
            )
            candidate_list = data(client.get("/api/behavior-candidates"))
            candidate_detail = data(
                client.get(f"/api/behavior-candidates/{approved_candidate_id}")
            )
            assert approved_candidate["status"] == "pending_review"
            assert rejected_candidate["status"] == "pending_review"
            assert any(
                item["candidate_pack_id"] == approved_candidate_id
                for item in candidate_list
            )
            assert candidate_detail["created_from_run_id"] == run_id

            approved = data(
                client.post(
                    f"/api/behavior-candidates/{approved_candidate_id}/approve",
                    json={"reviewer": "integration", "reason": "verified"},
                )
            )
            assert approved["status"] == "approved"
            assert approved["enabled"] is True

            rolled_back = data(
                client.post(
                    f"/api/behavior-candidates/{approved_candidate_id}/rollback",
                    json={"reviewer": "integration", "reason": "post_check"},
                )
            )
            assert rolled_back["status"] == "pending_review"
            assert rolled_back["enabled"] is False

            rejected = data(
                client.post(
                    f"/api/behavior-candidates/{rejected_candidate_id}/reject",
                    json={"reviewer": "integration", "reason": "not_safe"},
                )
            )
            assert rejected["status"] == "rejected"
            assert rejected["enabled"] is False
            assert (
                client.post(
                    f"/api/behavior-candidates/{rejected_candidate_id}/approve",
                    json={"reviewer": "integration"},
                ).status_code
                == 400
            )

            diagnostic = data(
                client.post(
                    "/api/diagnostics/ingest",
                    json={
                        "machine_name": machine_name,
                        "role": "worker",
                        "status": "available",
                        "report_type": "integration_test",
                        "payload": {"run_id": run_id},
                        "source_path": source_path,
                    },
                )
            )
            diagnostics = data(client.get("/api/diagnostics"))
            assert diagnostic["report_type"] == "integration_test"
            assert any(item["source_path"] == source_path for item in diagnostics)
        finally:
            _cleanup_postgres_test_data(database.connection, run_id, suffix)
