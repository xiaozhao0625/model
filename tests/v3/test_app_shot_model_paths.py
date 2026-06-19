from pathlib import Path

from ai_screenshot_platform.v3.model.registry import UiModelRegistry


def test_showui_provider_defaults_to_app_shot_model_dir(monkeypatch, tmp_path):
    model_root = tmp_path / "models"
    monkeypatch.setenv("APP_SHOT_MODELS", str(model_root))

    health = UiModelRegistry().health()
    showui = next(item for item in health if item.provider == "showui")

    assert Path(showui.details["model_dir"]) == model_root / "showui" / "ShowUI-2B"
