from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_folder_watch_smoke_uses_folder_parameter():
    script = (REPO_ROOT / "scripts/v3/smoke_v3_folder_watch.ps1").read_text(encoding="utf-8")

    assert "V3_SMOKE_FOLDER" in script
    assert "runs/v3_smoke_input" not in script
