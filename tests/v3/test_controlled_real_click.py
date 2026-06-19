import json

from ai_screenshot_platform.v3.action.action_loop import ActionLoop
from ai_screenshot_platform.v3.action.click_executor import ClickExecutor
from ai_screenshot_platform.v3.model.base import UiModelProvider
from ai_screenshot_platform.v3.model.registry import UiModelRegistry
from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import (
    ActionDecision,
    FusedCandidate,
    ModelClickCandidate,
    ModelRequest,
    ModelResult,
    OcrResult,
    OcrTextBox,
    ProviderHealth,
    SceneClassification,
    V3TaskConfig,
)
from ai_screenshot_platform.v3.storage.run_store import V3RunStore


class StaticOcrProvider(OcrProvider):
    provider_name = "static"

    def __init__(self, boxes: list[OcrTextBox]) -> None:
        self.boxes = boxes

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=True)

    def recognize(self, image_path: str) -> OcrResult:
        return OcrResult(provider=self.provider_name, status="ok", text_boxes=self.boxes)


class StaticUiModelProvider(UiModelProvider):
    provider_name = "static_ui_model"

    def __init__(self, candidates: list[ModelClickCandidate]) -> None:
        self.candidates = candidates

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=True)

    def classify_scene(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            provider=self.provider_name,
            status="ok",
            scene=SceneClassification(scene_class="software_ui", confidence=0.95, reason="test"),
        )

    def propose_visual_candidates(self, request: ModelRequest) -> ModelResult:
        return self.rank_click_candidates(request)

    def rank_click_candidates(self, request: ModelRequest) -> ModelResult:
        return ModelResult(provider=self.provider_name, status="ok", candidates=self.candidates)


def test_click_executor_requires_explicit_real_click_arm():
    candidate = FusedCandidate(
        label="Start",
        source="ocr_box",
        bbox=[0, 0, 20, 20],
        click_x=10,
        click_y=10,
        confidence=0.9,
        reason="test",
        final_score=0.8,
    )
    decision = ActionDecision(action="click", allowed=True, reason="allowed", candidate=candidate)
    clicks: list[tuple[int, int]] = []

    disabled = ClickExecutor(click_backend=lambda x, y: clicks.append((x, y))).execute(decision)
    enabled = ClickExecutor(
        allow_real_click=True,
        click_backend=lambda x, y: clicks.append((x, y)),
    ).execute(decision)

    assert disabled["executed"] is False
    assert disabled["reason"] == "real_click_disabled_by_default"
    assert enabled["executed"] is True
    assert enabled["clicked"] == [10, 10]
    assert clicks == [(10, 10)]


def test_runtime_real_click_uses_safe_ocr_candidate_and_writes_audit(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = _runtime_with_controlled_clicks(tmp_path, clicks)
    run = runtime.create_run(
        V3TaskConfig(
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    actions = runtime.actions_for_run(run.run_id)

    assert actions[0]["result"]["executed"] is True
    assert actions[0]["result"]["clicked"] == [30, 20]
    assert actions[0]["source_candidate_id"] == "ocr_box:Start:20:10:40:30"
    assert actions[0]["safety_result"]["reason"] == "allowed"
    assert actions[0]["result"]["status"] == "no_effect"
    assert clicks == [(30, 20)]
    run_dir = tmp_path / "runs" / run.run_id
    meta_dir = run_dir / "meta"
    assert (meta_dir / "actions.jsonl").is_file()
    assert (meta_dir / "events.jsonl").is_file()
    assert (meta_dir / "candidates.jsonl").is_file()
    assert (meta_dir / "ocr.jsonl").is_file()
    action_entry = _read_jsonl(meta_dir / "actions.jsonl")[0]
    assert action_entry["label"] == "Start"
    assert action_entry["before_image"].endswith("english.png")
    assert action_entry["after_image"].endswith("english.png")


def test_runtime_lists_actions_without_evaluating_or_clicking(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = _runtime_with_controlled_clicks(tmp_path, clicks)
    run = runtime.create_run(
        V3TaskConfig(
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    actions = runtime.list_actions(run.run_id)

    assert actions == []
    assert clicks == []
    assert not (tmp_path / "runs" / run.run_id / "meta" / "actions.jsonl").exists()


def test_runtime_evaluates_action_without_clicking(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = _runtime_with_controlled_clicks(tmp_path, clicks)
    run = runtime.create_run(
        V3TaskConfig(
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    actions = runtime.evaluate_action(run.run_id)

    assert actions[0]["label"] == "Start"
    assert actions[0]["result"]["executed"] is False
    assert actions[0]["result"]["status"] == "evaluated"
    assert actions[0]["result"]["reason"] == "evaluation_only"
    assert clicks == []
    assert runtime.list_actions(run.run_id)[0]["result"]["status"] == "evaluated"


def test_runtime_stops_after_max_actions(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = _runtime_with_controlled_clicks(tmp_path, clicks)
    run = runtime.create_run(
        V3TaskConfig(
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    runtime.actions_for_run(run.run_id)
    second = runtime.actions_for_run(run.run_id)

    assert second[0]["result"]["executed"] is False
    assert second[0]["result"]["status"] == "stopped"
    assert second[0]["result"]["reason"] == "max_actions_reached"
    assert clicks == [(30, 20)]


def test_runtime_does_not_real_click_without_safe_ocr_candidate(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        model_registry=UiModelRegistry(
            [
                StaticUiModelProvider(
                    [
                        ModelClickCandidate(
                            label="V3 English UI Test",
                            source="showui",
                            bbox=[57, 1, 97, 41],
                            click_x=77,
                            click_y=21,
                            confidence=0.99,
                            reason="model_top",
                        )
                    ]
                )
            ]
        ),
        ocr_provider=StaticOcrProvider([]),
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )
    run = runtime.create_run(
        V3TaskConfig(
            target_language="en",
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    actions = runtime.actions_for_run(run.run_id)

    assert actions[0]["result"]["executed"] is False
    assert actions[0]["result"]["reason"] == "no_safe_ocr_candidate"
    assert clicks == []


def test_runtime_does_not_real_click_rejected_images(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = _runtime_with_controlled_clicks(tmp_path, clicks)
    run = runtime.create_run(
        V3TaskConfig(
            target_language="zh",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    record = runtime.ingest_image(run.run_id, str(image))

    actions = runtime.actions_for_run(run.run_id)

    assert record.bucket == "rejected"
    assert actions[0]["result"]["executed"] is False
    assert actions[0]["result"]["reason"] == "image_bucket_rejected"
    assert clicks == []


def _runtime_with_controlled_clicks(tmp_path, clicks: list[tuple[int, int]]) -> V3Runtime:
    ocr_provider = StaticOcrProvider(
        [
            OcrTextBox(text="Login", bbox=[100, 10, 130, 30], confidence=0.95),
            OcrTextBox(text="Start", bbox=[20, 10, 40, 30], confidence=0.9),
            OcrTextBox(text="Next", bbox=[50, 10, 80, 30], confidence=0.88),
        ]
    )
    model_provider = StaticUiModelProvider(
        [
            ModelClickCandidate(
                label="main_window",
                source="showui",
                bbox=[0, 0, 200, 100],
                click_x=100,
                click_y=50,
                confidence=0.99,
                reason="model_top",
            )
        ]
    )
    return V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        model_registry=UiModelRegistry([model_provider]),
        ocr_provider=ocr_provider,
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
