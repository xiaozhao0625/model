from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.model_gateway.contracts import (  # noqa: E402
    ActRequest,
    ActionType,
    GroundRequest,
    ModelTaskType,
    SceneClass,
    SceneClassifyRequest,
)
from ai_screenshot_platform.common.model_gateway.gateway_service import (  # noqa: E402
    ModelGatewayService,
)
from ai_screenshot_platform.common.model_gateway.provider_config import (  # noqa: E402
    ProviderConfigLoader,
)
from ai_screenshot_platform.common.model_gateway.provider_registry import (  # noqa: E402
    ProviderRegistry,
)
from ai_screenshot_platform.common.model_gateway.providers.stub_providers import (  # noqa: E402
    create_stub_provider,
)


PROVIDERS_CONFIG_PATH = REPO_ROOT / "configs" / "model_gateway" / "providers.example.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local Model Gateway mock flow.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


def build_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    for config in ProviderConfigLoader.load(PROVIDERS_CONFIG_PATH):
        registry.register(config, create_stub_provider(config))
    return registry


def count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    return len([line for line in path.read_text(encoding="utf-8").splitlines() if line])


def run_mock(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    registry = build_registry()

    scene_provider = registry.select_for_task(ModelTaskType.SCENE_CLASSIFY)[0]
    ground_provider = registry.select_for_task(ModelTaskType.GROUND)[0]
    act_provider = registry.select_for_task(ModelTaskType.ACT)[0]

    scene_service = ModelGatewayService(scene_provider, run_dir=run_dir)
    ground_service = ModelGatewayService(ground_provider, run_dir=run_dir)
    act_service = ModelGatewayService(act_provider, run_dir=run_dir)

    screenshot_path = str(run_dir / "mock_screen.webp")
    scene_result = scene_service.scene_classify(
        SceneClassifyRequest(
            app_id=args.app_id,
            run_id=args.run_id,
            screenshot_path=screenshot_path,
            context={},
        )
    )
    ground_result = ground_service.ground(
        GroundRequest(
            app_id=args.app_id,
            run_id=args.run_id,
            screenshot_path=screenshot_path,
            target_description="continue button",
            context={},
        )
    )
    safe_action = act_service.act(
        ActRequest(
            app_id=args.app_id,
            run_id=args.run_id,
            screenshot_path=screenshot_path,
            scene_class=SceneClass.MENU,
            instruction="click the visible continue button",
        )
    )
    risky_action = act_service.act(
        ActRequest(
            app_id=args.app_id,
            run_id=args.run_id,
            screenshot_path=screenshot_path,
            scene_class=SceneClass.MENU,
            instruction="请处理验证码后继续",
        )
    )

    audit_log_path = run_dir / "model_gateway.log"
    return {
        "app_id": args.app_id,
        "run_id": args.run_id,
        "provider_name": act_provider.provider_name,
        "scene_provider_name": scene_provider.provider_name,
        "ground_provider_name": ground_provider.provider_name,
        "act_provider_name": act_provider.provider_name,
        "scene_class": scene_result.scene_class.value,
        "ground_found": ground_result.found,
        "safe_action_type": safe_action.action_type.value,
        "safe_blocked": safe_action.action_type
        in {ActionType.REQUEST_MANUAL, ActionType.ABORT},
        "risky_action_type": risky_action.action_type.value,
        "risky_blocked": risky_action.action_type
        in {ActionType.REQUEST_MANUAL, ActionType.ABORT},
        "audit_log_path": str(audit_log_path),
        "audit_event_count": count_jsonl(audit_log_path),
    }


def main() -> None:
    print(json.dumps(run_mock(parse_args()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
