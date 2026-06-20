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


class PathAwareOcrProvider(OcrProvider):
    provider_name = "path_aware"

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=True)

    def recognize(self, image_path: str) -> OcrResult:
        if "after_risk" in image_path:
            boxes = [OcrTextBox(text="Payment", bbox=[20, 10, 80, 30], confidence=0.95)]
        else:
            boxes = [OcrTextBox(text="Start", bbox=[20, 10, 40, 30], confidence=0.95)]
        return OcrResult(provider=self.provider_name, status="ok", text_boxes=boxes)


class SparseAfterOcrProvider(OcrProvider):
    provider_name = "sparse_after"

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=True)

    def recognize(self, image_path: str) -> OcrResult:
        if "after_sparse" in image_path:
            boxes = [OcrTextBox(text="A", bbox=[20, 10, 30, 30], confidence=0.95)]
        else:
            boxes = [OcrTextBox(text="Start", bbox=[20, 10, 40, 30], confidence=0.95)]
        return OcrResult(provider=self.provider_name, status="ok", text_boxes=boxes)


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
    assert actions[0]["result"]["click_backend"] == "custom_backend"
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
    assert action_entry["result"]["click_backend"] == "custom_backend"


def test_runtime_records_no_effect_when_after_image_hash_matches(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"same-image")
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

    action = runtime.execute_action(run.run_id)[0]
    effect = _read_jsonl(tmp_path / "runs" / run.run_id / "meta" / "effect.jsonl")[0]

    assert action["result"]["status"] == "no_effect"
    assert effect["status"] == "no_effect"
    assert effect["before_sha256"] == effect["after_sha256"]


def test_runtime_records_ui_changed_when_after_image_hash_differs(tmp_path):
    before = tmp_path / "english.png"
    after = tmp_path / "after_changed.png"
    before.write_bytes(b"before-image")
    after.write_bytes(b"after-image")
    clicks: list[tuple[int, int]] = []
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider([OcrTextBox(text="Start", bbox=[20, 10, 40, 30], confidence=0.95)]),
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )
    runtime._capture_after_image = lambda run_id, action_index, before_image: str(after)
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
    runtime.ingest_image(run.run_id, str(before))

    action = runtime.execute_action(run.run_id)[0]
    effect = _read_jsonl(tmp_path / "runs" / run.run_id / "meta" / "effect.jsonl")[0]

    assert action["result"]["status"] == "ui_changed"
    assert effect["status"] == "ui_changed"
    assert effect["before_sha256"] != effect["after_sha256"]


def test_runtime_marks_safe_menu_click_ui_change_as_menu_opened(tmp_path):
    before = tmp_path / "english.png"
    after = tmp_path / "after_menu.png"
    before.write_bytes(b"before-image")
    after.write_bytes(b"after-menu-image")
    clicks: list[tuple[int, int]] = []
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider([OcrTextBox(text="File", bbox=[20, 30, 40, 50], confidence=0.95)]),
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )
    runtime._capture_after_image = lambda run_id, action_index, before_image: str(after)
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    runtime.ingest_image(run.run_id, str(before))

    action = runtime.execute_action(run.run_id)[0]

    assert action["result"]["status"] == "menu_opened"


def test_runtime_requests_rollback_when_after_ocr_has_risk_term(tmp_path):
    before = tmp_path / "english.png"
    after = tmp_path / "after_risk.png"
    before.write_bytes(b"before-image")
    after.write_bytes(b"after-risk-image")
    clicks: list[tuple[int, int]] = []
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=PathAwareOcrProvider(),
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )
    runtime._capture_after_image = lambda run_id, action_index, before_image: str(after)
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
    runtime.ingest_image(run.run_id, str(before))

    action = runtime.execute_action(run.run_id)[0]
    effect = _read_jsonl(tmp_path / "runs" / run.run_id / "meta" / "effect.jsonl")[0]
    rollback = _read_jsonl(tmp_path / "runs" / run.run_id / "meta" / "rollback.jsonl")[0]

    assert action["result"]["status"] == "rollback_requested"
    assert effect["status"] == "rollback_requested"
    assert effect["rollback_reason"] == "after_ocr_risk_terms:payment"
    assert rollback["reason"] == "after_ocr_risk_terms:payment"
    assert rollback["sequence"][:3] == ["esc", "alt_left", "backspace"]


def test_runtime_does_not_rollback_after_action_only_for_sparse_ocr_text(tmp_path):
    before = tmp_path / "english.png"
    after = tmp_path / "after_sparse.png"
    before.write_bytes(b"before-image")
    after.write_bytes(b"after-sparse-image")
    clicks: list[tuple[int, int]] = []
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=SparseAfterOcrProvider(),
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )
    runtime._capture_after_image = lambda run_id, action_index, before_image: str(after)
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
    runtime.ingest_image(run.run_id, str(before))

    action = runtime.execute_action(run.run_id)[0]
    effect = _read_jsonl(tmp_path / "runs" / run.run_id / "meta" / "effect.jsonl")[0]

    assert action["result"]["status"] == "ui_changed"
    assert effect["status"] == "ui_changed"
    assert "rollback_reason" not in effect
    assert not (tmp_path / "runs" / run.run_id / "meta" / "rollback.jsonl").exists()


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


def test_runtime_uses_latest_accepted_image_when_newest_frame_is_near_duplicate(tmp_path):
    accepted = tmp_path / "accepted.png"
    duplicate = tmp_path / "duplicate.png"
    accepted.write_bytes(b"same-frame")
    duplicate.write_bytes(b"same-frame")
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
    first = runtime.ingest_image(run.run_id, str(accepted))
    newest = runtime.ingest_image(run.run_id, str(duplicate))

    actions = runtime.actions_for_run(run.run_id)

    assert first.bucket == "accepted"
    assert newest.bucket == "rejected"
    assert newest.reject_reason == "near_duplicate"
    assert actions[0]["result"]["executed"] is True
    assert actions[0]["before_image"].endswith("accepted.png")
    assert actions[0]["result"]["reason"] != "image_bucket_rejected"
    assert clicks == [(30, 20)]


def test_pc_app_action_selection_skips_top_tab_and_uses_safe_toolbar_label(tmp_path):
    image = tmp_path / "sumatra_toolbar.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(text="Home", bbox=[52, 15, 96, 36], confidence=0.95),
                OcrTextBox(text="Find:", bbox=[372, 42, 443, 63], confidence=0.95),
            ]
        ),
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                target_client_rect=(0, 28, 1200, 900),
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    action = runtime.actions_for_run(run.run_id)[0]

    assert action["label"] == "find"
    assert action["result"]["executed"] is True
    assert clicks == [(400, 52)]


def test_pc_app_document_body_candidate_is_content_area_and_not_clickable(tmp_path):
    image = tmp_path / "sumatra_body.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(
                    text="Sample paragraph 12: OCR should detect stable English text and menu states.",
                    bbox=[248, 485, 915, 505],
                    confidence=0.99,
                )
            ]
        ),
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                target_client_rect=(0, 28, 1200, 900),
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    record = runtime.ingest_image(run.run_id, str(image))

    candidates = runtime.candidates(run.run_id)
    action = runtime.actions_for_run(run.run_id)[0]
    audited_candidates = _read_jsonl(tmp_path / "runs" / run.run_id / "meta" / "candidates.jsonl")[-1]["candidates"]

    assert record.bucket == "accepted"
    assert candidates[0]["candidate_region_type"] == "content_area"
    assert candidates[0]["blocked"] is True
    assert candidates[0]["block_reason"] == "content_area_not_clickable"
    assert "ocr_box" in audited_candidates[0]["candidate_source"]
    assert audited_candidates[0]["text"].startswith("Sample paragraph")
    assert audited_candidates[0]["score"] == candidates[0]["final_score"]
    assert audited_candidates[0]["blocked_reason"] == "content_area_not_clickable"
    assert action["result"]["executed"] is False
    assert action["result"]["reason"] == "content_area_not_clickable"
    assert action["candidate_region_type"] == "content_area"
    assert action["blocked_reason"] == "content_area_not_clickable"
    assert clicks == []


def test_pc_app_unsafe_chrome_candidate_is_blocked_and_audited(tmp_path):
    image = tmp_path / "sumatra_print.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider([OcrTextBox(text="Print", bbox=[10, 42, 48, 64], confidence=0.95)]),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    candidates = runtime.candidates(run.run_id)

    print_candidate = next(candidate for candidate in candidates if candidate["label"] == "Print")
    assert print_candidate["candidate_region_type"] == "unsafe_chrome"
    assert print_candidate["blocked"] is True
    assert print_candidate["block_reason"] == "unsafe_chrome"


def test_pc_app_candidates_include_safe_ui_chrome_labels(tmp_path):
    image = tmp_path / "notepadpp.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(text="Start", bbox=[20, 100, 80, 130], confidence=0.95),
                OcrTextBox(text="文件", bbox=[8, 30, 42, 50], confidence=0.92),
            ]
        ),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    labels = {candidate["label"] for candidate in runtime.candidates(run.run_id)}

    assert "Start" in labels
    assert "文件" in labels


def test_pc_app_candidates_split_combined_safe_menu_bar_text(tmp_path):
    image = tmp_path / "notepadpp.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(text="Start", bbox=[20, 100, 80, 130], confidence=0.95),
                OcrTextBox(text="文件(F) 编辑(E) 搜索(S) 视图(V)", bbox=[4, 23, 260, 40], confidence=0.92),
            ]
        ),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    labels = {candidate["label"] for candidate in runtime.candidates(run.run_id)}

    assert {"文件", "编辑", "搜索", "视图"}.issubset(labels)


def test_pc_app_candidates_do_not_split_document_body_menu_words(tmp_path):
    image = tmp_path / "sumatra_body.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(
                    text="Safe menus for exploration: File, View, Go To, Zoom",
                    bbox=[343, 179, 851, 193],
                    confidence=0.99,
                ),
                OcrTextBox(text="V3 SumatraPDF English OCR Sample", bbox=[342, 112, 677, 132], confidence=0.99),
            ]
        ),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    labels = {candidate["label"] for candidate in runtime.candidates(run.run_id)}

    assert "file" not in labels
    assert "view" not in labels
    assert "go to" not in labels
    assert "zoom" not in labels
    body_candidate = next(candidate for candidate in runtime.candidates(run.run_id) if candidate["label"].startswith("Safe menus"))
    assert body_candidate["candidate_region_type"] == "content_area"
    assert body_candidate["blocked"] is True


def test_pc_app_winmerge_diff_body_is_content_area_and_not_clickable(tmp_path):
    image = tmp_path / "winmerge_diff.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(text="File Edit View Merge Tools Help", bbox=[6, 34, 290, 55], confidence=0.95),
                OcrTextBox(
                    text="line 4: this sentence exists only in the right comparison file",
                    bbox=[510, 248, 1010, 268],
                    confidence=0.95,
                ),
            ]
        ),
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                target_client_rect=(0, 28, 1200, 900),
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=1,
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    candidates = runtime.candidates(run.run_id)
    body_candidate = next(candidate for candidate in candidates if candidate["label"].startswith("line 4"))
    action = runtime.actions_for_run(run.run_id)[0]

    assert body_candidate["candidate_region_type"] == "content_area"
    assert body_candidate["blocked_reason"] == "content_area_not_clickable"
    assert action["candidate_region_type"] == "ui_chrome"
    assert action["result"]["executed"] is True
    assert clicks


def test_pc_app_winmerge_save_variants_are_unsafe_chrome(tmp_path):
    image = tmp_path / "winmerge_save.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(text="Save Left", bbox=[32, 58, 112, 76], confidence=0.95),
                OcrTextBox(text="Save Right", bbox=[32, 82, 120, 100], confidence=0.95),
                OcrTextBox(text="Save Merged", bbox=[32, 106, 140, 124], confidence=0.95),
            ]
        ),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    candidates = runtime.candidates(run.run_id)
    unsafe = {candidate["label"]: candidate for candidate in candidates}

    assert unsafe["Save Left"]["candidate_region_type"] == "unsafe_chrome"
    assert unsafe["Save Right"]["candidate_region_type"] == "unsafe_chrome"
    assert unsafe["Save Merged"]["candidate_region_type"] == "unsafe_chrome"


def test_pc_app_revisits_safe_ui_chrome_after_unique_labels_are_exhausted(tmp_path):
    image = tmp_path / "menu.png"
    image.write_bytes(b"not-empty")
    clicks: list[tuple[int, int]] = []
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider([OcrTextBox(text="File", bbox=[32, 40, 58, 58], confidence=0.95)]),
        action_loop=ActionLoop(
            executor=ClickExecutor(
                allow_real_click=True,
                target_client_rect=(0, 28, 800, 600),
                click_backend=lambda x, y: clicks.append((x, y)),
            )
        ),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
            enable_auto_click=True,
            observe_only=False,
            max_actions=2,
        )
    )
    runtime.ingest_image(run.run_id, str(image))

    first = runtime.execute_action(run.run_id)[0]
    second = runtime.execute_action(run.run_id)[0]

    assert first["result"]["executed"] is True
    assert second["result"]["executed"] is True
    assert first["candidate_region_type"] == "ui_chrome"
    assert second["candidate_region_type"] == "ui_chrome"
    assert len(clicks) == 2


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
