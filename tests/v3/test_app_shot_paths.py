from pathlib import Path

from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.v3.schemas import V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore


def test_run_store_defaults_to_app_shot_runs_v3(monkeypatch, tmp_path):
    runs_root = tmp_path / "runs"
    monkeypatch.setenv("APP_SHOT_RUNS", str(runs_root))

    store = V3RunStore()
    run = store.create_run(V3TaskConfig())

    assert Path(store.root) == runs_root / "v3"
    assert (runs_root / "v3" / run.run_id / "run.json").is_file()


def test_master_app_defaults_read_app_shot_env(monkeypatch, tmp_path):
    database = tmp_path / "master.db"
    data_root = tmp_path / "master-data"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setenv("DATA_ROOT", str(data_root))

    app = create_app()

    assert app.state.settings.database_url == f"sqlite:///{database}"
    assert app.state.settings.data_root == str(data_root)
