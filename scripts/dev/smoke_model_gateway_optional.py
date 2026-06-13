from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.model_gateway.contracts import (  # noqa: E402
    ActRequest,
    GroundRequest,
    SceneClass,
    SceneClassifyRequest,
)
from ai_screenshot_platform.common.model_gateway.gateway_service import (  # noqa: E402
    ModelGatewayService,
)
from ai_screenshot_platform.model_gateway.runtime_manager import (  # noqa: E402
    ModelRuntimeManager,
)


def main() -> None:
    run_dir = REPO_ROOT / "runs" / "smoke_model_gateway_optional"
    manager = ModelRuntimeManager(
        manifest_path=REPO_ROOT / "configs" / "model_gateway" / "model_manifest.example.json",
        runtime_config_path=REPO_ROOT / "configs" / "model_gateway" / "provider_runtime.example.json",
    )
    provider = manager.select_provider("act")
    service = ModelGatewayService(provider=provider, run_dir=run_dir)
    scene = service.scene_classify(
        SceneClassifyRequest(
            app_id="model_smoke",
            run_id="optional",
            screenshot_path="screen.webp",
        )
    )
    ground = service.ground(
        GroundRequest(
            app_id="model_smoke",
            run_id="optional",
            screenshot_path="screen.webp",
            target_description="button",
        )
    )
    act = service.act(
        ActRequest(
            app_id="model_smoke",
            run_id="optional",
            screenshot_path="screen.webp",
            scene_class=SceneClass.MENU,
            instruction="wait",
        )
    )
    risky = service.act(
        ActRequest(
            app_id="model_smoke",
            run_id="optional",
            screenshot_path="screen.webp",
            scene_class=SceneClass.SHOP,
            instruction="验证码 payment",
        )
    )
    model_files_available = any(item.available for item in manager.check_health())
    print(
        json.dumps(
            {
                "selected_provider": provider.provider_name,
                "fallback_used": provider.provider_name == "mock",
                "scene_classify_status": scene.scene_class.value,
                "ground_status": "found" if ground.found else "not_found",
                "act_status": act.action_type.value,
                "blocked_by_safety": risky.action_type.value == "request_manual",
                "model_files_available": model_files_available,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
