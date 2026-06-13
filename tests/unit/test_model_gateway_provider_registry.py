import inspect
import json
import sys
from pathlib import Path

import pytest

from ai_screenshot_platform.common.model_gateway.contracts import (
    ActRequest,
    ActionType,
    ModelTaskType,
    SceneClass,
)
from ai_screenshot_platform.common.model_gateway.gateway_service import (
    ModelGatewayService,
)
from ai_screenshot_platform.common.model_gateway.provider_config import (
    ProviderConfigError,
    ProviderConfigLoader,
    ProviderType,
)
from ai_screenshot_platform.common.model_gateway.provider_registry import (
    ProviderCapabilityError,
    ProviderRegistry,
)
from ai_screenshot_platform.common.model_gateway.providers import stub_providers
from ai_screenshot_platform.common.model_gateway.providers.stub_providers import (
    OmniParserStubProvider,
    QwenVLStubProvider,
    ShowUIStubProvider,
    UITarsStubProvider,
    create_stub_provider,
)


EXAMPLE_CONFIG = Path("configs/model_gateway/providers.example.json")


def make_act_request() -> ActRequest:
    return ActRequest(
        app_id="demo_app",
        run_id="demo_run",
        screenshot_path="runs/demo/screen.webp",
        scene_class=SceneClass.MENU,
        instruction="click continue",
    )


def make_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    for config in ProviderConfigLoader.load(EXAMPLE_CONFIG):
        registry.register(config, create_stub_provider(config))
    return registry


def test_providers_example_json_can_load():
    configs = ProviderConfigLoader.load(EXAMPLE_CONFIG)

    assert {config.provider_name for config in configs} >= {
        "mock",
        "ui_tars_stub",
        "showui_stub",
        "qwen_vl_stub",
        "omniparser_stub",
    }


def test_provider_config_fields_parse_correctly():
    config = ProviderConfigLoader.load(EXAMPLE_CONFIG)[0]

    assert config.provider_name == "mock"
    assert config.provider_type == ProviderType.MOCK
    assert config.enabled is True
    assert config.capabilities.supports_scene_classify is True
    assert config.capabilities.supports_ground is True
    assert config.capabilities.supports_act is True
    assert config.config["mode"] == "local_mock"


def test_registry_can_register_mock_provider():
    registry = make_registry()

    provider = registry.get("mock")

    assert provider.provider_name == "mock"


def test_registry_can_register_real_model_stub_providers():
    registry = make_registry()

    assert isinstance(registry.get("ui_tars_stub"), UITarsStubProvider)
    assert isinstance(registry.get("showui_stub"), ShowUIStubProvider)
    assert isinstance(registry.get("qwen_vl_stub"), QwenVLStubProvider)
    assert isinstance(registry.get("omniparser_stub"), OmniParserStubProvider)


def test_disabled_provider_is_not_listed_as_enabled():
    registry = make_registry()

    enabled_names = {config.provider_name for config in registry.list_enabled()}

    assert "disabled_mock" not in enabled_names


def test_select_for_scene_classify_filters_by_capability():
    registry = make_registry()

    providers = registry.select_for_task(ModelTaskType.SCENE_CLASSIFY)

    assert {provider.provider_name for provider in providers} == {
        "mock",
        "qwen_vl_stub",
    }


def test_select_for_ground_filters_by_capability():
    registry = make_registry()

    providers = registry.select_for_task(ModelTaskType.GROUND)

    assert {provider.provider_name for provider in providers} == {
        "mock",
        "showui_stub",
        "omniparser_stub",
    }


def test_select_for_act_filters_by_capability():
    registry = make_registry()

    providers = registry.select_for_task(ModelTaskType.ACT)

    assert {provider.provider_name for provider in providers} == {
        "mock",
        "ui_tars_stub",
    }


def test_provider_without_act_support_cannot_handle_act():
    provider = make_registry().get("showui_stub")

    with pytest.raises(ProviderCapabilityError, match="act"):
        provider.act(make_act_request())


def test_unknown_provider_type_raises_error(tmp_path):
    config_path = tmp_path / "providers.json"
    config_path.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "provider_name": "mystery",
                        "provider_type": "mystery_model",
                        "enabled": True,
                        "capabilities": {
                            "supports_scene_classify": True,
                            "supports_ground": False,
                            "supports_act": False,
                            "requires_gpu": False,
                            "default_device": "cpu",
                        },
                        "config": {},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProviderConfigError, match="unknown provider_type"):
        ProviderConfigLoader.load(config_path)


def test_stub_provider_does_not_execute_real_actions():
    provider = UITarsStubProvider("ui_tars_stub")

    proposal = provider.act(make_act_request())

    assert proposal.action_type in {ActionType.NO_OP, ActionType.REQUEST_MANUAL}
    assert not hasattr(proposal, "execute")


def test_stub_providers_do_not_import_real_model_libraries():
    source = inspect.getsource(stub_providers)

    assert "import torch" not in source
    assert "transformers" not in source
    assert "torch" not in sys.modules
    assert "transformers" not in sys.modules


def test_gateway_service_can_use_registry_mock_provider_for_safe_act(tmp_path):
    provider = make_registry().get("mock")
    service = ModelGatewayService(provider, run_dir=tmp_path)

    proposal = service.act(make_act_request())

    assert proposal.action_type == ActionType.NO_OP
    assert proposal.provider_name == "mock"
