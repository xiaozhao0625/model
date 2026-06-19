from ai_screenshot_platform.v3.schemas import V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore


def test_run_store_creates_and_summarizes(tmp_path):
    store = V3RunStore(tmp_path)
    run = store.create_run(V3TaskConfig(save_root=str(tmp_path)))
    store.update_status(run.run_id, "running")
    summary = store.summary(run.run_id, ocr_ready=True, model_ready=False, safety_gate_ready=True)
    assert summary.status == "running"
    assert summary.observe_only is True
    assert summary.auto_click_ready is False
