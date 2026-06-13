from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SINGLE_NODE_CONFIG = REPO_ROOT / "configs" / "topology" / "single_node_dev.example.json"
FOUR_NODE_CONFIG = REPO_ROOT / "configs" / "topology" / "four_node_prod.example.json"
MODEL_MANIFEST = REPO_ROOT / "configs" / "model_gateway" / "model_manifest.example.json"


def run_json_command(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_single_node_dev_topology_passes_check_script():
    output = run_json_command(
        "scripts/env/check_topology_config.py",
        "--config",
        str(SINGLE_NODE_CONFIG),
    )

    assert output["valid"] is True
    assert output["topology_name"] == "single_node_dev"
    assert output["worker_count"] >= 3


def test_four_node_prod_topology_passes_check_script():
    output = run_json_command(
        "scripts/env/check_topology_config.py",
        "--config",
        str(FOUR_NODE_CONFIG),
    )

    assert output["valid"] is True
    assert output["topology_name"] == "four_node_prod"
    assert set(output["machine_ids"]) >= {"M0", "W1", "W2", "W3"}


def test_model_manifest_passes_check_script():
    output = run_json_command(
        "scripts/models/check_model_manifest.py",
        "--manifest",
        str(MODEL_MANIFEST),
    )

    assert output["valid"] is True
    assert set(output["model_ids"]) >= {
        "ui_tars",
        "showui",
        "qwen_vl",
        "omniparser",
        "gui_actor",
        "os_atlas",
    }


def test_single_node_dev_has_required_worker_roles():
    config = load_json(SINGLE_NODE_CONFIG)
    worker_types = {worker["worker_type"] for worker in config["workers"]}

    assert "pc_game" in worker_types
    assert "pc_app_web" in worker_types
    assert "android" in worker_types


def test_four_node_prod_has_required_machines():
    config = load_json(FOUR_NODE_CONFIG)
    machine_ids = {machine["machine_id"] for machine in config["machines"]}

    assert machine_ids >= {"M0", "W1", "W2", "W3"}


def test_model_manifest_contains_required_models():
    manifest = load_json(MODEL_MANIFEST)
    model_ids = {model["model_id"] for model in manifest["models"]}

    assert model_ids >= {
        "ui_tars",
        "showui",
        "qwen_vl",
        "omniparser",
        "gui_actor",
        "os_atlas",
    }


def test_model_manifest_load_mode_allows_only_resident_or_on_demand():
    manifest = load_json(MODEL_MANIFEST)
    load_modes = {model["load_mode"] for model in manifest["models"]}

    assert load_modes <= {"resident", "on_demand"}


def test_check_local_dev_env_outputs_valid_json():
    output = run_json_command("scripts/env/check_local_dev_env.py")

    assert output["valid"] is True
    assert output["python_version"]
    assert output["platform"]
    assert output["gpu"]["required"] is False


def test_model_manifest_does_not_require_model_files_to_exist():
    manifest = load_json(MODEL_MANIFEST)
    missing_paths = [
        model["local_path"]
        for model in manifest["models"]
        if not (REPO_ROOT / model["local_path"]).exists()
    ]

    assert missing_paths
    assert run_json_command(
        "scripts/models/check_model_manifest.py",
        "--manifest",
        str(MODEL_MANIFEST),
    )["valid"] is True
