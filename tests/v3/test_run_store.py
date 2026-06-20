from ai_screenshot_platform.v3.schemas import V3TaskConfig
from ai_screenshot_platform.v3.schemas import V3ImageRecord
from ai_screenshot_platform.v3.storage.run_store import V3RunStore


def test_run_store_creates_and_summarizes(tmp_path):
    store = V3RunStore(tmp_path)
    run = store.create_run(V3TaskConfig(save_root=str(tmp_path)))
    store.update_status(run.run_id, "running")
    summary = store.summary(run.run_id, ocr_ready=True, model_ready=False, safety_gate_ready=True)
    assert summary.status == "running"
    assert summary.observe_only is True
    assert summary.auto_click_ready is False


def test_summary_includes_reject_distribution_and_ocr_gate(tmp_path):
    store = V3RunStore(tmp_path)
    run = store.create_run(
        V3TaskConfig(
            save_root=str(tmp_path),
            enable_auto_click=True,
            observe_only=False,
        )
    )
    store.add_image(
        run.run_id,
        V3ImageRecord(
            image_id="blank",
            path="blank.png",
            bucket="rejected",
            reject_reason="no_text",
            valid=False,
            content_hash="sha:blank",
            near_duplicate=False,
        ),
    )
    store.add_image(
        run.run_id,
        V3ImageRecord(
            image_id="dup",
            path="dup.png",
            bucket="rejected",
            reject_reason="near_duplicate",
            valid=True,
            content_hash="sha:dup",
            near_duplicate=True,
        ),
    )

    summary = store.summary(
        run.run_id,
        ocr_ready=True,
        model_ready=True,
        safety_gate_ready=True,
        ocr_gpu_ready=False,
        ocr_performance_ready=False,
        ocr_production_ready=False,
        readiness_blockers=["ocr_gpu_not_ready", "ocr_performance_not_ready"],
    )

    assert summary.reject_reason_distribution == {"no_text": 1, "near_duplicate": 1}
    assert summary.ocr_gpu_ready is False
    assert summary.ocr_performance_ready is False
    assert summary.ocr_production_ready is False
    assert summary.full_auto_capture_ready is False
    assert summary.readiness_blockers == ["ocr_gpu_not_ready", "ocr_performance_not_ready"]


def test_summary_includes_review_action_state_and_frame_pump_metrics(tmp_path):
    store = V3RunStore(tmp_path)
    run = store.create_run(V3TaskConfig(save_root=str(tmp_path)))
    store.add_image(
        run.run_id,
        V3ImageRecord(
            image_id="review",
            path="review.png",
            bucket="manual_review",
            reject_reason="ocr_unavailable",
        ),
    )
    run_dir = tmp_path / run.run_id
    (run_dir / "meta").mkdir(parents=True, exist_ok=True)
    (run_dir / "meta" / "folder_watch_summary.json").write_text(
        """{
  "failed": 0,
  "quarantined": 0,
  "action_state_count": 3,
  "frame_pump_restart_count": 2,
  "frame_pump_heartbeat": {
    "frame_index": 151,
    "status": "running"
  }
}""",
        encoding="utf-8",
    )

    summary = store.summary(run.run_id, ocr_ready=True, model_ready=True, safety_gate_ready=True)

    assert summary.manual_review_count == 1
    assert summary.action_state_count == 3
    assert summary.frame_pump_restart_count == 2
    assert summary.frame_pump_heartbeat == {"frame_index": 151, "status": "running"}


def test_summary_includes_candidate_region_action_counts(tmp_path):
    store = V3RunStore(tmp_path)
    run = store.create_run(V3TaskConfig(save_root=str(tmp_path)))
    store.append_meta_jsonl(
        run.run_id,
        "actions.jsonl",
        {
            "candidate_region_type": "content_area",
            "result": {"executed": False, "status": "blocked", "reason": "content_area_not_clickable"},
        },
    )
    store.append_meta_jsonl(
        run.run_id,
        "actions.jsonl",
        {
            "candidate_region_type": "ui_chrome",
            "result": {"executed": True, "status": "menu_opened", "reason": "real_click_executed"},
        },
    )
    store.append_meta_jsonl(
        run.run_id,
        "actions.jsonl",
        {
            "candidate_region_type": "unsafe_chrome",
            "result": {"executed": False, "status": "blocked", "reason": "unsafe_chrome"},
        },
    )

    summary = store.summary(run.run_id, ocr_ready=True, model_ready=True, safety_gate_ready=True)

    assert summary.content_area_blocked_count == 1
    assert summary.ui_chrome_click_count == 1
    assert summary.unsafe_chrome_blocked_count == 1
