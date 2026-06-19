from pathlib import Path

from PIL import Image

from ai_screenshot_platform.v3.model import showui_provider
from ai_screenshot_platform.v3.model.omniparser_provider import OmniParserProvider
from ai_screenshot_platform.v3.model.prompt_templates import SHOWUI_RANK_PROMPT
from ai_screenshot_platform.v3.model.registry import UiModelRegistry
from ai_screenshot_platform.v3.model.showui_provider import ShowUiProvider
from ai_screenshot_platform.v3.schemas import ModelRequest


class FakeRunner:
    def __init__(self, output: str) -> None:
        self.output = output
        self.queries: list[str] = []

    def run(self, image_path: str, query: str) -> str:
        self.queries.append(query)
        return self.output


def test_parse_showui_point_accepts_relative_coordinate_lists():
    assert showui_provider.parse_showui_point("[0.25, 0.75]") == (0.25, 0.75)
    assert showui_provider.parse_showui_point("{'action': 'CLICK', 'position': [0.49, 0.42]}") == (0.49, 0.42)


def test_showui_rank_prompt_requests_relative_coordinates():
    assert "relative coordinate" in SHOWUI_RANK_PROMPT
    assert "[x, y]" in SHOWUI_RANK_PROMPT


def test_showui_provider_ranks_candidates_from_model_output(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (200, 100), "white").save(image_path)
    runner = FakeRunner("{'action': 'CLICK', 'value': 'Start', 'position': [0.25, 0.5]}")
    provider = ShowUiProvider(model_dir=str(tmp_path), enabled=True, runner=runner)

    result = provider.rank_click_candidates(
        ModelRequest(
            screenshot_path=str(image_path),
            task_context={"goal": "Start the app"},
        )
    )

    assert result.status == "ok"
    assert result.candidates[0].source == "showui"
    assert result.candidates[0].click_x == 50
    assert result.candidates[0].click_y == 50
    assert result.candidates[0].label == "Start"
    assert "Start the app" in runner.queries[0]


def test_preload_showui_torch_runtime_only_runs_when_enabled(monkeypatch):
    imported: list[str] = []

    def fake_import(name: str):
        imported.append(name)

    monkeypatch.delenv("APP_SHOT_ENABLE_SHOWUI", raising=False)
    showui_provider.preload_showui_torch_runtime(importer=fake_import)
    assert imported == []

    monkeypatch.setenv("APP_SHOT_ENABLE_SHOWUI", "1")
    showui_provider.preload_showui_torch_runtime(importer=fake_import)
    assert imported == ["torch"]


def test_registry_prefers_ready_showui_over_mock(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (200, 100), "white").save(image_path)
    runner = FakeRunner("[0.25, 0.5]")
    registry = UiModelRegistry()
    registry.providers[1] = ShowUiProvider(model_dir=str(tmp_path), enabled=True, runner=runner)

    result = registry.rank_click_candidates(
        ModelRequest(
            screenshot_path=str(image_path),
            task_context={"goal": "Start"},
        )
    )

    assert result.status == "ok"
    assert result.provider == "showui"
    assert result.candidates[0].source == "showui"


def test_showui_unimplemented_methods_return_model_status(tmp_path: Path):
    provider = ShowUiProvider(model_dir=str(tmp_path), enabled=True)

    result = provider.classify_scene(ModelRequest(screenshot_path="mock.png"))

    assert result.status == "degraded"
    assert result.error == "enabled"


def test_omniparser_blocked_status_maps_to_model_status():
    result = OmniParserProvider(license_accepted=True).classify_scene(ModelRequest(screenshot_path="mock.png"))

    assert result.status == "degraded"
