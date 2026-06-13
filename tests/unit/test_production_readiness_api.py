from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings


def make_client(tmp_path: Path) -> TestClient:
    settings = MasterSettings(
        database_url=f"sqlite:///{tmp_path / 'master.db'}",
        redis_url="memory://",
        env="test",
        data_root=tmp_path,
    )
    return TestClient(create_app(settings))


def data(response):
    payload = response.json()
    assert payload["code"] == 0
    return payload["data"]


def test_quality_report_ingest_list_and_detail(tmp_path):
    with make_client(tmp_path) as client:
        report = data(
            client.post(
                "/api/quality-reports/ingest",
                json={
                    "app_id": "web_portal",
                    "run_id": "run_quality_api",
                    "total_images": 10,
                    "accepted_count": 8,
                    "rejected_count": 2,
                    "quality_pass_rate": 0.8,
                    "browser_chrome_count": 1,
                    "taskbar_count": 1,
                    "ocr_risk_hit_count": 1,
                    "reject_reason_distribution": {"browser_chrome_visible": 1},
                },
            )
        )
        listed = data(client.get("/api/quality-reports"))
        detail = data(client.get("/api/quality-reports/run_quality_api"))

        assert report["run_id"] == "run_quality_api"
        assert listed[0]["accepted_count"] == 8
        assert detail["reject_reason_distribution"]["browser_chrome_visible"] == 1


def test_ocr_report_ingest_status_list_and_detail(tmp_path):
    with make_client(tmp_path) as client:
        data(
            client.post(
                "/api/ocr/reports/ingest",
                json={
                    "app_id": "android_shop",
                    "run_id": "run_ocr_api",
                    "provider": "mock",
                    "available": True,
                    "status": "available",
                    "risk_hits": ["captcha"],
                    "scene_hints": ["login", "captcha"],
                    "paddleocr_optional_status": "unavailable",
                    "easyocr_optional_status": "unavailable",
                },
            )
        )
        status = data(client.get("/api/ocr/status"))
        listed = data(client.get("/api/ocr/reports"))
        detail = data(client.get("/api/ocr/reports/run_ocr_api"))

        assert status["provider"] == "mock"
        assert listed[0]["risk_hits"] == ["captcha"]
        assert detail["scene_hints"] == ["login", "captcha"]


def test_tool_health_and_diagnostics_ingest(tmp_path):
    with make_client(tmp_path) as client:
        health = data(
            client.post(
                "/api/tool-health/ingest",
                json={
                    "machine_name": "W3",
                    "worker_id": "android_w3",
                    "worker_type": "android",
                    "status": "skipped",
                    "tools": {"ADB": "unavailable"},
                    "android": {
                        "adb_available": False,
                        "devices": [],
                        "selected_device": None,
                        "screencap_status": "skipped",
                        "ui_dump_status": "skipped",
                        "ocr_fallback_status": "skipped",
                        "input_status": "disabled",
                    },
                },
            )
        )
        diagnostics = data(
            client.post(
                "/api/diagnostics/ingest",
                json={
                    "machine_name": "M0",
                    "role": "master",
                    "status": "available",
                    "report_type": "machine_ready",
                    "payload": {"python": "ok"},
                },
            )
        )

        assert health["tools"]["ADB"] == "unavailable"
        assert data(client.get("/api/tool-health/android"))["adb_available"] is False
        assert diagnostics["report_type"] == "machine_ready"
        assert data(client.get("/api/diagnostics"))[0]["status"] == "available"


def test_behavior_candidate_ingest_review_and_rollback(tmp_path):
    with make_client(tmp_path) as client:
        candidate = data(
            client.post(
                "/api/behavior-candidates/ingest",
                json={
                    "candidate_pack_id": "candidate_api_001",
                    "base_pack_id": "fps_mock_v1",
                    "game_type": "fps",
                    "version": "2.0",
                    "status": "pending_review",
                    "issues": ["duplicate_ratio_high"],
                    "recommendations": ["reduce repeated movement"],
                    "rollback_target": "fps_mock_v1",
                    "created_from_run_id": "run_001",
                    "pack_content": {"pack_id": "candidate_api_001"},
                },
            )
        )
        approved = data(client.post("/api/behavior-candidates/candidate_api_001/approve", json={"reviewer": "qa", "reason": "ok"}))
        rollback = data(client.post("/api/behavior-candidates/candidate_api_001/rollback", json={"reviewer": "qa", "reason": "regression"}))
        detail = data(client.get("/api/behavior-candidates/candidate_api_001"))

        assert candidate["status"] == "pending_review"
        assert approved["status"] == "approved"
        assert approved["enabled"] is True
        assert rollback["status"] == "pending_review"
        assert rollback["enabled"] is False
        assert detail["rollback_target"] == "fps_mock_v1"


def test_empty_readiness_lists_do_not_500(tmp_path):
    with make_client(tmp_path) as client:
        assert data(client.get("/api/quality-reports")) == []
        assert data(client.get("/api/ocr/reports")) == []
        assert data(client.get("/api/behavior-candidates")) == []
        assert data(client.get("/api/diagnostics")) == []
