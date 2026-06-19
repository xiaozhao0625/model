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
    assert '"1"' in text
