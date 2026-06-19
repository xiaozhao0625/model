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


def test_folder_watch_loop_smoke_runs_long_worker():
    script = (REPO_ROOT / "scripts/v3/smoke_v3_folder_watch_loop.ps1").read_text(encoding="utf-8")

    assert "run_folder_watch_loop" in script
    assert "DurationSeconds = 600" in script
    assert "MaxIterations" in script
    assert "folder_watch_summary.json" in script
    assert "observe_only=True" in script
    assert "enable_auto_click=False" in script


def test_model_env_check_defaults_to_app_shot_models():
    script = (REPO_ROOT / "scripts/v3/model/check_model_env.ps1").read_text(encoding="utf-8")

    assert "APP_SHOT_HOME" in script
    assert "APP_SHOT_MODELS" in script
    assert '"D:\\work\\app-shot"' in script
    assert '[string]$ModelRoot = "models"' not in script


def test_local_html_observe_smoke_is_observe_only():
    script = (REPO_ROOT / "scripts/v3/smoke_v3_local_html_observe.ps1").read_text(encoding="utf-8")

    assert "local_html_observe" in script
    assert "run_folder_watch_once" in script
    assert "observe_only=True" in script
    assert "enable_auto_click=False" in script
    assert "execute_action" not in script
    assert "actions/execute" not in script
    assert "--headless" in script
    assert "app_shot_env.ps1" in script
    assert "APP_SHOT_OBS_OUTPUT" in script


def test_local_html_controlled_click_smoke_requires_explicit_arm():
    script = (REPO_ROOT / "scripts/v3/smoke_v3_local_html_controlled_click.ps1").read_text(encoding="utf-8")

    assert "local_html_controlled_click" in script
    assert "ExecuteRealClick" in script
    assert "APP_SHOT_ALLOW_REAL_CLICK" in script
    assert "APP_SHOT_CAPTURE_AFTER_CLICK" in script
    assert "observe_only=False" in script
    assert "enable_auto_click=True" in script
    assert "max_actions=1" in script
    assert "execute_action" in script
    assert "run_folder_watch_once" in script
    assert "app_shot_env.ps1" in script
    assert "ImageGrab.grab(bbox=" in script
    assert "click_backend=offset_click" in script
