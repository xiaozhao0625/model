import json
import subprocess
import sys
from pathlib import Path

from ai_screenshot_platform.common.model_gateway.contracts import ActionType
from ai_screenshot_platform.common.model_gateway.provider_config import (
    ProviderConfigLoader,
)
from ai_screenshot_platform.common.model_gateway.provider_registry import (
    ProviderRegistry,
)
from ai_screenshot_platform.common.model_gateway.providers.stub_providers import (
    create_stub_provider,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
P3_DRY_RUN_SCRIPT = REPO_ROOT / "scripts" / "dev" / "mock_model_gateway_run.py"
PROVIDERS_EXAMPLE = REPO_ROOT / "configs" / "model_gateway" / "providers.example.json"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def run_dry_run(tmp_path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(P3_DRY_RUN_SCRIPT),
            "--run-dir",
            str(tmp_path),
            "--app-id",
            "demo_app",
            "--run-id",
            "demo_p3_run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_dry_run_outputs_valid_json(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["app_id"] == "demo_app"
    assert output["run_id"] == "demo_p3_run"


def test_dry_run_can_load_providers_example_json():
    configs = ProviderConfigLoader.load(PROVIDERS_EXAMPLE)

    assert configs


def test_registry_can_select_available_provider():
    registry = ProviderRegistry()
    for config in ProviderConfigLoader.load(PROVIDERS_EXAMPLE):
        registry.register(config, create_stub_provider(config))

    assert registry.select_for_task("scene_classify")
    assert registry.select_for_task("ground")
    assert registry.select_for_task("act")


def test_dry_run_scene_classify_has_result(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["scene_class"]
    assert output["scene_provider_name"]


def test_dry_run_ground_has_result(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["ground_found"] is True
    assert output["ground_provider_name"]


def test_safe_act_is_not_falsely_blocked(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["safe_action_type"] == ActionType.NO_OP.value
    assert output["safe_blocked"] is False


def test_risky_act_is_blocked(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["risky_blocked"] is True


def test_risky_act_returns_request_manual_or_abort(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["risky_action_type"] in {
        ActionType.REQUEST_MANUAL.value,
        ActionType.ABORT.value,
    }


def test_model_gateway_log_exists_under_run_dir(tmp_path):
    output = run_dry_run(tmp_path)
    audit_log_path = Path(output["audit_log_path"])

    assert audit_log_path == tmp_path.resolve() / "model_gateway.log"
    assert audit_log_path.is_file()


def test_model_gateway_log_is_valid_jsonl(tmp_path):
    output = run_dry_run(tmp_path)

    events = read_jsonl(Path(output["audit_log_path"]))

    assert events
    for event in events:
        assert event["task_type"] == "act"
        assert event["app_id"] == "demo_app"
        assert event["run_id"] == "demo_p3_run"


def test_audit_event_count_is_positive(tmp_path):
    output = run_dry_run(tmp_path)

    assert output["audit_event_count"] > 0


def test_dry_run_does_not_generate_real_model_files(tmp_path):
    run_dry_run(tmp_path)
    forbidden_suffixes = {".bin", ".pt", ".pth", ".safetensors", ".onnx"}

    assert not [
        path
        for path in tmp_path.rglob("*")
        if path.is_file() and path.suffix in forbidden_suffixes
    ]
