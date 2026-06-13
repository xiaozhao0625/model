from __future__ import annotations

import json
import os
from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.model_gateway.contracts import ModelTaskType
from ai_screenshot_platform.model_gateway.model_health import ModelHealthChecker
from ai_screenshot_platform.model_gateway.model_paths import ModelPathResolver
from ai_screenshot_platform.model_gateway.runtime_manager import ModelRuntimeManager


MANIFEST = Path("configs/model_gateway/model_manifest.example.json")
RUNTIME_CONFIG = Path("configs/model_gateway/provider_runtime.example.json")


def test_model_manifest_contains_required_models_and_p11_fields():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    models = {model["model_id"]: model for model in manifest["models"]}

    assert {"ui_tars", "showui", "qwen_vl", "omniparser", "gui_actor", "os_atlas"} <= set(models)
    for model in models.values():
        assert model["load_mode"] in {"resident", "on_demand", "disabled"}
        assert isinstance(model["expected_files"], list)
        assert isinstance(model["download"], dict)
        assert isinstance(model["runtime"], dict)


def test_model_path_resolver_uses_model_root_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("MODEL_ROOT", str(tmp_path / "custom_models"))

    paths = ModelPathResolver(MANIFEST).resolve_all()
    showui = next(item for item in paths if item.model_id == "showui")

    assert showui.local_path == tmp_path / "custom_models" / "showui"
    assert showui.exists is False
    assert showui.load_mode in {"resident", "on_demand", "disabled"}


def test_model_health_reports_missing_files_without_loading_models(monkeypatch, tmp_path):
    monkeypatch.setenv("MODEL_ROOT", str(tmp_path / "models"))

    results = ModelHealthChecker(MANIFEST).check_all()

    assert results
    assert {result.status for result in results} <= {
        "missing_files",
        "disabled",
        "available",
        "unavailable",
    }
    assert any(result.status == "missing_files" for result in results)


def test_model_runtime_manager_lists_models_and_selects_fallback_provider(tmp_path):
    manager = ModelRuntimeManager(
        manifest_path=MANIFEST,
        runtime_config_path=RUNTIME_CONFIG,
    )

    models = manager.list_models()
    provider = manager.select_provider(ModelTaskType.ACT)

    assert len(models) >= 6
    assert provider.provider_name == "mock"


def test_model_runtime_manager_does_not_add_formal_run_statuses():
    statuses = {status.value for status in RunStatus}

    assert "model_loading" not in statuses
    assert "model_unavailable" not in statuses
    assert "provider_runtime_failed" not in statuses
