from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_folder_watch_smoke_uses_folder_parameter():
    script = (REPO_ROOT / "scripts/v3/smoke_v3_folder_watch.ps1").read_text(encoding="utf-8")

    assert "V3_SMOKE_FOLDER" in script
    assert "runs/v3_smoke_input" not in script
    assert "venvs\\v3\\Scripts\\python.exe" in script


def test_model_mock_smoke_has_local_fallback():
    script = (REPO_ROOT / "scripts/v3/smoke_v3_model_mock.ps1").read_text(encoding="utf-8")

    assert "FallbackToLocal" in script
    assert "UiModelRegistry" in script


def test_folder_watch_worker_smoke_runs_worker_once():
    script = (REPO_ROOT / "scripts/v3/smoke_v3_folder_watch_worker.ps1").read_text(encoding="utf-8")

    assert "run_folder_watch_once" in script
    assert "folder_watch_summary.json" in script
    assert "APP_SHOT_OBS_OUTPUT" in script
    assert 'os.environ["APP_SHOT_RUNS"]' not in script
    assert 'app_name="folder_watch_worker_smoke"' not in script


def test_model_env_check_defaults_to_app_shot_models():
    script = (REPO_ROOT / "scripts/v3/model/check_model_env.ps1").read_text(encoding="utf-8")

    assert "APP_SHOT_HOME" in script
    assert "APP_SHOT_MODELS" in script
    assert '"D:\\work\\app-shot"' in script
    assert '[string]$ModelRoot = "models"' not in script
