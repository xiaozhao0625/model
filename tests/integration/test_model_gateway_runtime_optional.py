from __future__ import annotations

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
from ai_screenshot_platform.model_gateway.runtime_manager import ModelRuntimeManager


def test_model_gateway_runtime_falls_back_to_mock_when_models_missing(tmp_path):
    manager = ModelRuntimeManager(
        manifest_path="configs/model_gateway/model_manifest.example.json",
        runtime_config_path="configs/model_gateway/provider_runtime.example.json",
    )
    provider = manager.select_provider("act")
    service = ModelGatewayService(provider=provider, run_dir=tmp_path)

    scene = service.scene_classify(
        SceneClassifyRequest(
            app_id="app",
            run_id="run",
            screenshot_path="screen.webp",
        )
    )
    ground = service.ground(
        GroundRequest(
            app_id="app",
            run_id="run",
            screenshot_path="screen.webp",
            target_description="button",
        )
    )
    safe = service.act(
        ActRequest(
            app_id="app",
            run_id="run",
            screenshot_path="screen.webp",
            scene_class=SceneClass.MENU,
            instruction="wait for the menu",
        )
    )
    risky = service.act(
        ActRequest(
            app_id="app",
            run_id="run",
            screenshot_path="screen.webp",
            scene_class=SceneClass.SHOP,
            instruction="支付 checkout",
        )
    )

    assert provider.provider_name == "mock"
    assert scene.provider_name == "mock"
    assert ground.provider_name == "mock"
    assert safe.action_type.value in {"no_op", "request_manual"}
    assert risky.action_type.value == "request_manual"
    assert "payment" in risky.risk_flags
    assert (Path(tmp_path) / "model_gateway.log").exists()
