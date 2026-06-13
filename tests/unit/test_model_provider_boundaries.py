from __future__ import annotations

import ast
import importlib
from pathlib import Path

from ai_screenshot_platform.common.model_gateway.contracts import (
    ActRequest,
    GroundRequest,
    SceneClass,
    SceneClassifyRequest,
)
from ai_screenshot_platform.common.model_gateway.gateway_service import (
    ModelGatewayService,
)
from ai_screenshot_platform.model_gateway.providers.gui_actor_provider import (
    GuiActorProvider,
)
from ai_screenshot_platform.model_gateway.providers.omniparser_provider import (
    OmniParserProvider,
)
from ai_screenshot_platform.model_gateway.providers.os_atlas_provider import (
    OsAtlasProvider,
)
from ai_screenshot_platform.model_gateway.providers.qwen_vl_provider import (
    QwenVLProvider,
)
from ai_screenshot_platform.model_gateway.providers.showui_provider import (
    ShowUIProvider,
)
from ai_screenshot_platform.model_gateway.providers.ui_tars_provider import (
    UITarsProvider,
)


PROVIDER_MODULES = [
    "ai_screenshot_platform.model_gateway.providers.showui_provider",
    "ai_screenshot_platform.model_gateway.providers.omniparser_provider",
    "ai_screenshot_platform.model_gateway.providers.qwen_vl_provider",
    "ai_screenshot_platform.model_gateway.providers.ui_tars_provider",
    "ai_screenshot_platform.model_gateway.providers.gui_actor_provider",
    "ai_screenshot_platform.model_gateway.providers.os_atlas_provider",
]


def test_provider_modules_do_not_import_real_model_libraries_at_top_level():
    for module_name in PROVIDER_MODULES:
        module = importlib.import_module(module_name)
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        top_level_imports = [
            node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

        imported_names = {
            alias.name
            for node in top_level_imports
            for alias in getattr(node, "names", [])
        }
        forbidden_modules = {"to" + "rch", "trans" + "formers"}
        assert imported_names.isdisjoint(forbidden_modules)


def test_real_provider_boundaries_return_unavailable_without_model_files(tmp_path):
    providers = [
        ShowUIProvider(model_path=tmp_path / "missing_showui"),
        OmniParserProvider(model_path=tmp_path / "missing_omniparser"),
        QwenVLProvider(model_path=tmp_path / "missing_qwen"),
        UITarsProvider(model_path=tmp_path / "missing_ui_tars"),
        GuiActorProvider(model_path=tmp_path / "missing_gui_actor"),
        OsAtlasProvider(model_path=tmp_path / "missing_os_atlas"),
    ]

    scene_request = SceneClassifyRequest(
        app_id="app",
        run_id="run",
        screenshot_path="screen.webp",
    )
    ground_request = GroundRequest(
        app_id="app",
        run_id="run",
        screenshot_path="screen.webp",
        target_description="button",
    )
    act_request = ActRequest(
        app_id="app",
        run_id="run",
        screenshot_path="screen.webp",
        scene_class=SceneClass.MENU,
        instruction="wait",
    )

    for provider in providers:
        assert provider.health().available is False
        assert provider.scene_classify(scene_request).provider_name == provider.provider_name
        assert provider.ground(ground_request).provider_name == provider.provider_name
        assert provider.act(act_request).provider_name == provider.provider_name


def test_provider_output_still_passes_safety_gate(tmp_path):
    service = ModelGatewayService(
        provider=UITarsProvider(model_path=tmp_path / "missing_ui_tars"),
        run_dir=tmp_path,
    )

    result = service.act(
        ActRequest(
            app_id="app",
            run_id="run",
            screenshot_path="screen.webp",
            scene_class=SceneClass.SHOP,
            instruction="please click payment checkout",
        )
    )

    assert result.action_type.value == "request_manual"
    assert "payment" in result.risk_flags
