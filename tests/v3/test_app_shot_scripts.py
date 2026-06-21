import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_app_shot_scripts_are_present_and_path_scoped():
    expected = [
        "scripts/v3/start_v3_backend_app_shot.ps1",
        "scripts/v3/start_v3_web_app_shot.ps1",
        "scripts/v3/model/install_paddleocr_app_shot.ps1",
        "scripts/v3/model/check_paddleocr_app_shot.ps1",
        "scripts/v3/model/download_showui_app_shot.ps1",
        "scripts/v3/model/check_showui_app_shot.ps1",
        "scripts/v3/model/start_showui_server_app_shot.ps1",
        "scripts/v3/model/check_paddle_device_app_shot.ps1",
        "scripts/v3/model/install_paddle_gpu_app_shot.ps1",
        "scripts/v3/model/check_ocr_gpu_performance_app_shot.ps1",
        "scripts/v3/model/smoke_paddle_gpu_ocr_app_shot.ps1",
        "scripts/v3/model/smoke_showui_inference_app_shot.ps1",
        "scripts/v3/action/diagnose_input_gateway_app_shot.ps1",
        "scripts/v3/action/smoke_input_gateway_app_shot.ps1",
        "scripts/v3/power/save_power_policy_app_shot.ps1",
        "scripts/v3/power/prevent_sleep_for_capture_app_shot.ps1",
        "scripts/v3/power/restore_power_policy_app_shot.ps1",
        "scripts/v3/power/smoke_power_policy_app_shot.ps1",
        "scripts/v3/capture/run_sumatrapdf_real_capture_app_shot.ps1",
        "scripts/v3/capture/start_sumatrapdf_frame_pump_app_shot.ps1",
        "scripts/v3/capture/stop_sumatrapdf_frame_pump_app_shot.ps1",
        "scripts/v3/capture/smoke_sumatrapdf_frame_pump_app_shot.ps1",
        "scripts/v3/capture/run_winmerge_real_capture_app_shot.ps1",
        "scripts/v3/capture/start_winmerge_frame_pump_app_shot.ps1",
        "scripts/v3/capture/stop_winmerge_frame_pump_app_shot.ps1",
        "scripts/v3/capture/smoke_winmerge_frame_pump_app_shot.ps1",
        "scripts/v3/report/build_batch_capture_report_app_shot.ps1",
        "scripts/v3/report/explain_duplicate_decisions_app_shot.ps1",
    ]

    for script in expected:
        text = (REPO_ROOT / script).read_text(encoding="utf-8")
        assert "D:\\work\\app-shot" in text


def test_showui_app_shot_download_script_is_manual_gated():
    text = (REPO_ROOT / "scripts/v3/model/download_showui_app_shot.ps1").read_text(encoding="utf-8")

    assert "manual-gated" in text
    assert "snapshot_download" not in text
    assert "huggingface-cli download" not in text


def test_backend_app_shot_script_enables_real_paddleocr():
    text = (REPO_ROOT / "scripts/v3/start_v3_backend_app_shot.ps1").read_text(encoding="utf-8")

    assert "APP_SHOT_ENABLE_PADDLEOCR" in text
    assert "APP_SHOT_ENABLE_SHOWUI" in text
    assert '"1"' in text


def test_paddleocr_check_uses_project_provider_not_bare_import():
    text = (REPO_ROOT / "scripts/v3/model/check_paddleocr_app_shot.ps1").read_text(encoding="utf-8")

    assert "PaddleOcrProvider" in text
    assert "import paddleocr" not in text


def test_showui_smoke_requires_explicit_enable_flag():
    text = (REPO_ROOT / "scripts/v3/model/smoke_showui_inference_app_shot.ps1").read_text(encoding="utf-8")

    assert "APP_SHOT_ENABLE_SHOWUI" in text
    assert "ShowUiProvider" in text


def test_showui_server_script_enables_provider():
    text = (REPO_ROOT / "scripts/v3/model/start_showui_server_app_shot.ps1").read_text(encoding="utf-8")

    assert "APP_SHOT_ENABLE_SHOWUI" in text
    assert '"1"' in text


def test_showui_check_reports_explicit_enable_flag():
    text = (REPO_ROOT / "scripts/v3/model/check_showui_app_shot.ps1").read_text(encoding="utf-8")

    assert "APP_SHOT_ENABLE_SHOWUI" in text
    assert "weights_present_but_disabled" in text


def test_gpu_paddle_install_script_uses_isolated_v3_gpu_venv():
    text = (REPO_ROOT / "scripts/v3/model/install_paddle_gpu_app_shot.ps1").read_text(encoding="utf-8")

    assert "venvs\\v3-gpu" in text
    assert "pip freeze" in text
    assert "paddlepaddle-gpu" in text
    assert "is_compiled_with_cuda" in text


def test_ocr_gpu_performance_script_reports_readiness_json():
    text = (REPO_ROOT / "scripts/v3/model/check_ocr_gpu_performance_app_shot.ps1").read_text(encoding="utf-8")

    assert "ocr_gpu_ready" in text
    assert "ocr_performance_ready" in text
    assert "ocr_production_ready" in text
    assert "full_auto_capture_ready" in text
    assert "full_frame_ms" in text
    assert "roi_ms" in text
    assert "scaled_ms" in text
    assert "cache_hit_ms" in text


def test_gpu_ocr_smoke_covers_multilingual_and_real_window_targets():
    text = (REPO_ROOT / "scripts/v3/model/smoke_paddle_gpu_ocr_app_shot.ps1").read_text(encoding="utf-8")

    assert "is_compiled_with_cuda" in text
    assert "english" in text
    assert "japanese" in text
    assert "korean" in text
    assert "notepadplusplus" in text.lower()


def test_input_gateway_diagnosis_script_reports_audited_readiness_json():
    text = (REPO_ROOT / "scripts/v3/action/diagnose_input_gateway_app_shot.ps1").read_text(encoding="utf-8")

    assert "input_gateway_diagnosis.json" in text
    assert "GetCursorPos" in text
    assert "SetCursorPos" in text
    assert "SendInput" in text
    assert "pyautogui" in text
    assert "integrity" in text
    assert "interactive_desktop" in text
    assert "input_gateway_ready" in text


def test_input_gateway_smoke_requires_audited_backend_and_no_sendkeys():
    text = (REPO_ROOT / "scripts/v3/action/smoke_input_gateway_app_shot.ps1").read_text(encoding="utf-8")

    assert "click_backend" in text
    assert "actions.jsonl" in text
    assert "risk button" in text
    assert "SendKeys" not in text


def test_power_policy_scripts_save_prevent_restore_structured_json():
    save = (REPO_ROOT / "scripts/v3/power/save_power_policy_app_shot.ps1").read_text(encoding="utf-8")
    prevent = (REPO_ROOT / "scripts/v3/power/prevent_sleep_for_capture_app_shot.ps1").read_text(encoding="utf-8")
    restore = (REPO_ROOT / "scripts/v3/power/restore_power_policy_app_shot.ps1").read_text(encoding="utf-8")
    smoke = (REPO_ROOT / "scripts/v3/power/smoke_power_policy_app_shot.ps1").read_text(encoding="utf-8")

    assert "power_policy_before_capture.json" in save
    assert "power_policy_capture_active.json" in prevent
    assert "power_policy_restored.json" in restore
    assert "ConvertTo-Json" in save
    assert "monitor-timeout-ac" in prevent
    assert "monitor-timeout-dc" in prevent
    assert "standby-timeout-ac" in prevent
    assert "standby-timeout-dc" in prevent
    assert "hibernate-timeout-ac" in prevent
    assert "hibernate-timeout-dc" in prevent
    assert "finally" in smoke
    assert "restore_power_policy_app_shot.ps1" in smoke
    assert "SendKeys" not in save + prevent + restore + smoke


def test_sumatrapdf_real_capture_script_wraps_power_policy_and_audited_input():
    text = (REPO_ROOT / "scripts/v3/capture/run_sumatrapdf_real_capture_app_shot.ps1").read_text(encoding="utf-8")

    assert "save_power_policy_app_shot.ps1" in text
    assert "prevent_sleep_for_capture_app_shot.ps1" in text
    assert "restore_power_policy_app_shot.ps1" in text
    assert "finally" in text
    assert "diagnose_input_gateway_app_shot.ps1" in text
    assert "APP_SHOT_ALLOW_REAL_CLICK" in text
    assert "sumatrapdf_real_auto_explore_sample" in text
    assert "max_actions=20" in text
    assert "target_accepted_min=50" in text
    assert "SendKeys" not in text


def test_sumatrapdf_frame_pump_scripts_have_heartbeat_and_atomic_sidecars():
    start = (REPO_ROOT / "scripts/v3/capture/start_sumatrapdf_frame_pump_app_shot.ps1").read_text(encoding="utf-8")
    stop = (REPO_ROOT / "scripts/v3/capture/stop_sumatrapdf_frame_pump_app_shot.ps1").read_text(encoding="utf-8")
    smoke = (REPO_ROOT / "scripts/v3/capture/smoke_sumatrapdf_frame_pump_app_shot.ps1").read_text(encoding="utf-8")
    runner_text = start + stop + smoke

    assert "frame_pump_heartbeat.json" in runner_text
    assert "sumatrapdf_frame_pump.pid" in runner_text
    assert "window_title" in start
    assert "frame_path" in start
    assert "capture_reason" in start
    assert "action_id" in start
    assert "ui_state_hint" in start
    assert "frame_index" in start
    assert ".tmp" in start
    assert "Replace" in start or "replace" in start
    assert "window_occluded_or_minimized" in start
    assert "MinFrames" in smoke
    assert "SendKeys" not in runner_text


def test_sumatrapdf_real_capture_script_restarts_stale_frame_pump():
    text = (REPO_ROOT / "scripts/v3/capture/run_sumatrapdf_real_capture_app_shot.ps1").read_text(encoding="utf-8")

    assert "start_sumatrapdf_frame_pump_app_shot.ps1" in text
    assert "stop_sumatrapdf_frame_pump_app_shot.ps1" in text
    assert "frame_pump_restart_count" in text
    assert "frame_pump_heartbeat" in text
    assert "stale" in text


def test_sumatrapdf_real_capture_script_forces_english_ui_and_tracks_action_attempts():
    text = (REPO_ROOT / "scripts/v3/capture/run_sumatrapdf_real_capture_app_shot.ps1").read_text(encoding="utf-8")

    assert "SumatraPDF-settings.txt" in text
    assert "UiLanguage = en" in text
    assert "ShowMenubar = true" in text
    assert "action_attempts" in text
    assert "summary.accepted > 0" in text


def test_notepadplusplus_frame_pump_smoke_starts_missing_target_window():
    text = (REPO_ROOT / "scripts/v3/capture/smoke_frame_pump_app_shot.ps1").read_text(encoding="utf-8")

    assert "notepad++.exe" in text
    assert "Start-Process" in text
    assert "started_by_smoke" in text
    assert "CloseMainWindow" in text


def test_winmerge_real_capture_script_creates_fixture_and_blocks_destructive_actions():
    text = (REPO_ROOT / "scripts/v3/capture/run_winmerge_real_capture_app_shot.ps1").read_text(encoding="utf-8")

    assert "WinMergeU.exe" in text
    assert "WinMerge.exe" in text
    assert "test-files\\winmerge\\left.txt" in text
    assert "test-files\\winmerge\\right.txt" in text
    assert "winmerge_real_auto_explore_sample" in text
    assert "max_actions=20" in text
    assert "target_accepted_min=50" in text
    assert "Save Left" in text
    assert "Save Right" in text
    assert "Save Merged" in text
    assert "winmerge_mojibake_menu_map" in text
    assert "menu_view" in text
    assert "menu_tools" in text
    assert "SendKeys" not in text


def test_winmerge_frame_pump_scripts_have_heartbeat_and_atomic_sidecars():
    start = (REPO_ROOT / "scripts/v3/capture/start_winmerge_frame_pump_app_shot.ps1").read_text(encoding="utf-8")
    stop = (REPO_ROOT / "scripts/v3/capture/stop_winmerge_frame_pump_app_shot.ps1").read_text(encoding="utf-8")
    smoke = (REPO_ROOT / "scripts/v3/capture/smoke_winmerge_frame_pump_app_shot.ps1").read_text(encoding="utf-8")
    runner_text = start + stop + smoke

    assert "frame_pump_heartbeat.json" in runner_text
    assert "winmerge_frame_pump.pid" in runner_text
    assert "winmerge_frame_" in start
    assert "window_title" in start
    assert "frame_path" in start
    assert "capture_reason" in start
    assert "action_id" in start
    assert "ui_state_hint" in start
    assert ".tmp" in start
    assert "MinFrames" in smoke
    assert "SendKeys" not in runner_text


def test_batch_capture_report_script_summarizes_quality_and_safety_contract():
    text = (REPO_ROOT / "scripts/v3/report/build_batch_capture_report_app_shot.ps1").read_text(encoding="utf-8")

    assert "v3_batch_capture_report.json" in text
    assert "v3_batch_capture_report.md" in text
    assert "accepted_by_ui_state_hint" in text
    assert "reject_reason_distribution" in text
    assert "action_count" in text
    assert "blocked_count" in text
    assert "risk_hit_count" in text
    assert "misclicked_titlebar_or_system_button" in text
    assert "dangerous_action_triggered" in text
    assert "accepted_target_met" in text
    assert "recommend_larger_scale" in text
    assert "exact_duplicate_count" in text
    assert "action_representative_accepted_count" in text
    assert "visual_difference_accepted_count" in text
    assert "periodic_static_rejected_count" in text
    assert "duplicate_policy_summary" in text
    assert "summary.json" in text
    assert "meta\\actions.jsonl" in text
    assert "meta\\candidates.jsonl" in text
    assert "SendKeys" not in text


def test_duplicate_explain_report_script_generates_json_and_markdown(tmp_path):
    app_home = tmp_path / "app-shot"
    run_id = "v3_test_duplicate_report"
    run_dir = app_home / "runs" / "v3" / run_id
    meta_dir = run_dir / "meta"
    meta_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "processed": 3,
                "accepted": 2,
                "rejected": 1,
                "near_duplicate_count": 1,
                "accepted_by_ui_state_hint": {"main_view": 1, "menu_file": 1},
                "accepted_by_capture_reason": {"periodic": 1, "after_action": 1},
                "reject_reason_distribution": {"near_duplicate": 1},
            }
        ),
        encoding="utf-8",
    )
    image_rows = [
        {
            "image_id": "frame_1",
            "path": "frame_1.png",
            "bucket": "accepted",
            "content_hash": "sha:1",
            "reject_reason": None,
            "meta": {"capture_reason": "periodic", "ui_state_hint": "main_view", "action_id": None},
            "duplicate_decision": {
                "duplicate_decision_reason": "first_frame_for_ui_state",
                "similarity_score": 0.0,
                "compared_with_image_id": None,
            },
        },
        {
            "image_id": "frame_2",
            "path": "frame_2.png",
            "bucket": "accepted",
            "content_hash": "sha:1",
            "reject_reason": None,
            "meta": {"capture_reason": "after_action", "ui_state_hint": "menu_file", "action_id": "action:1"},
            "duplicate_decision": {
                "duplicate_decision_reason": "after_action_representative_accepted",
                "similarity_score": 1.0,
                "compared_with_image_id": "frame_1",
                "accepted_as_action_representative": True,
                "representative_group_key": "action:1|menu_file",
                "representative_index": 1,
                "representative_limit": 3,
            },
        },
        {
            "image_id": "frame_3",
            "path": "frame_3.png",
            "bucket": "rejected",
            "content_hash": "sha:1",
            "reject_reason": "near_duplicate",
            "meta": {"capture_reason": "periodic", "ui_state_hint": "main_view", "action_id": None},
            "duplicate_decision": {
                "duplicate_decision_reason": "periodic_static_frame_rejected",
                "similarity_score": 1.0,
                "duplicate_threshold": 1.0,
                "compared_with_image_id": "frame_1",
            },
        },
    ]
    (run_dir / "images.jsonl").write_text("\n".join(json.dumps(row) for row in image_rows), encoding="utf-8")
    for name in ["actions.jsonl", "candidates.jsonl", "ocr.jsonl", "rollback.jsonl"]:
        (meta_dir / name).write_text("", encoding="utf-8")
    (meta_dir / "folder_watch_summary.json").write_text("{}", encoding="utf-8")

    script = REPO_ROOT / "scripts/v3/report/explain_duplicate_decisions_app_shot.ps1"
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-AppShotHome",
            str(app_home),
            "-RunId",
            run_id,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report_json = app_home / "reports" / f"duplicate_explain_{run_id}.json"
    report_md = app_home / "reports" / f"duplicate_explain_{run_id}.md"
    report = json.loads(report_json.read_text(encoding="utf-8-sig"))
    assert report["run_id"] == run_id
    assert report["near_duplicate_count"] == 1
    assert report["action_representative_accepted_count"] == 1
    assert report["periodic_static_rejected_count"] == 1
    assert "accepted samples" in report_md.read_text(encoding="utf-8-sig").lower()
