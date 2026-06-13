from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.common.runtime.run_session import (
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.workers.android.health_check import check_android_adb_health
from ai_screenshot_platform.workers.android.real_adb_adapter import (
    RealAdbAndroidDeviceAdapter,
)
from ai_screenshot_platform.workers.pc_app.health_check import check_pc_app_health
from ai_screenshot_platform.workers.pc_app.real_window_adapter import (
    RealPcAppWindowAdapter,
)
from ai_screenshot_platform.workers.pc_game.health_check import check_pc_game_health
from ai_screenshot_platform.workers.pc_game.real_ffmpeg_adapter import (
    RealFfmpegExtractAdapter,
)
from ai_screenshot_platform.workers.pc_game.real_obs_adapter import (
    RealObsCaptureAdapter,
)
from ai_screenshot_platform.workers.runtime.health import ToolHealth
from ai_screenshot_platform.workers.web.health_check import check_web_playwright_health
from ai_screenshot_platform.workers.web.real_playwright_adapter import (
    RealPlaywrightWebAdapter,
)
from ai_screenshot_platform.workers.web.stub_adapters import StubWebAutomationAdapter
from ai_screenshot_platform.workers.web.contracts import WebTargetConfig
from ai_screenshot_platform.workers.web.pipeline import WebStubPipeline


REAL_MODULES = [
    "ai_screenshot_platform.workers.web.real_playwright_adapter",
    "ai_screenshot_platform.workers.pc_app.real_window_adapter",
    "ai_screenshot_platform.workers.pc_game.real_obs_adapter",
    "ai_screenshot_platform.workers.pc_game.real_ffmpeg_adapter",
    "ai_screenshot_platform.workers.android.real_adb_adapter",
]


def test_real_adapter_health_checks_return_tool_health_without_real_tools():
    checks = [
        check_web_playwright_health(),
        check_pc_app_health()["pywinauto"],
        check_pc_game_health()["obs"],
        check_pc_game_health()["ffmpeg"],
        check_android_adb_health(),
    ]

    for health in checks:
        assert isinstance(health, ToolHealth)
        assert isinstance(health.available, bool)
        assert health.required_for
        assert health.reason


def test_real_adapters_import_without_starting_tools():
    for module_name in REAL_MODULES:
        module = importlib.import_module(module_name)

        assert module is not None


def test_real_adapter_modules_do_not_import_subprocess_at_module_top():
    for module_name in REAL_MODULES:
        module = importlib.import_module(module_name)
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        top_level_imports = [
            node
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

        assert not any(
            alias.name == "subprocess"
            for node in top_level_imports
            for alias in getattr(node, "names", [])
        )


def test_real_adapter_instances_expose_health_without_side_effects():
    adapters = [
        RealPlaywrightWebAdapter(),
        RealPcAppWindowAdapter(),
        RealObsCaptureAdapter(enabled=False),
        RealFfmpegExtractAdapter(enabled=False),
        RealAdbAndroidDeviceAdapter(enabled=False),
    ]

    for adapter in adapters:
        health = adapter.health()
        assert isinstance(health, ToolHealth)
        assert health.available is False


def test_stub_fallback_still_runs_to_capture_completed(tmp_path):
    session = LocalRunSession(
        RunSessionConfig(
            root_dir=tmp_path,
            app_id="web_app",
            run_id="web_stub_run",
            target_min=3,
        )
    )
    result = WebStubPipeline(
        session=session,
        automation_adapter=StubWebAutomationAdapter(),
    ).run(
        WebTargetConfig(
            app_id="web_app",
            url="https://example.invalid",
            viewport_width=800,
            viewport_height=600,
            content_area_only=True,
        )
    )

    assert result.status == RunStatus.CAPTURE_COMPLETED
    assert result.low_count == 3
    assert not (result.run_dir / "upload_manifest.json").exists()


def test_real_adapter_config_example_uses_skip_safe_defaults():
    config = json.loads(
        Path("configs/workers/real_adapters.example.json").read_text(encoding="utf-8")
    )

    assert config["web"]["mode"] == "stub"
    assert config["web"]["content_area_only"] is True
    assert config["pc_game"]["obs"]["enabled"] is False
    assert config["pc_game"]["ffmpeg"]["enabled"] is False
    assert config["android"]["adb"]["enabled"] is False


def test_p10_does_not_add_formal_run_statuses():
    statuses = {status.value for status in RunStatus}

    assert "real_capture_running" not in statuses
    assert "tool_unavailable" not in statuses
    assert "completed_max" not in statuses
