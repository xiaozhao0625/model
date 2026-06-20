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
