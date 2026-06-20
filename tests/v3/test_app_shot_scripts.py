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
