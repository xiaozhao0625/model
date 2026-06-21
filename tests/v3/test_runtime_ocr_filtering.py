from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import OcrResult, OcrTextBox, ProviderHealth, V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore
from PIL import Image


class StaticOcrProvider(OcrProvider):
    provider_name = "static"

    def __init__(self, boxes: list[OcrTextBox]) -> None:
        self.boxes = boxes
        self.calls = 0

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=True)

    def recognize(self, image_path: str) -> OcrResult:
        self.calls += 1
        return OcrResult(provider=self.provider_name, status="ok", text_boxes=self.boxes)


def test_ingest_accepts_image_with_target_language_text(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider([OcrTextBox(text="Start", bbox=[1, 2, 3, 4], confidence=0.9)]),
    )
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True))

    record = runtime.ingest_image(run.run_id, str(image))

    assert record.bucket == "accepted"
    assert record.reject_reason is None
    assert record.meta["ocr"]["provider"] == "static"


def test_ingest_rejects_image_without_required_text(tmp_path):
    image = tmp_path / "blank.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(store=V3RunStore(tmp_path / "runs"), ocr_provider=StaticOcrProvider([]))
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True))

    record = runtime.ingest_image(run.run_id, str(image))

    assert record.bucket == "rejected"
    assert record.reject_reason == "no_text"


def test_ingest_rejects_black_and_white_screen_images(tmp_path):
    black = tmp_path / "black.png"
    white = tmp_path / "white.png"
    Image.new("RGB", (320, 200), (0, 0, 0)).save(black)
    Image.new("RGB", (320, 200), (255, 255, 255)).save(white)
    runtime = V3Runtime(store=V3RunStore(tmp_path / "runs"), ocr_provider=StaticOcrProvider([]))
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True, save_root=str(tmp_path / "runs")))

    black_record = runtime.ingest_image(run.run_id, str(black))
    white_record = runtime.ingest_image(run.run_id, str(white))

    assert black_record.bucket == "rejected"
    assert black_record.reject_reason == "black_screen"
    assert black_record.valid is False
    assert white_record.bucket == "rejected"
    assert white_record.reject_reason == "white_screen"
    assert white_record.valid is False


def test_ingest_rejects_wrong_language_text(tmp_path):
    image = tmp_path / "wrong.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider([OcrTextBox(text="Start", bbox=[1, 2, 3, 4], confidence=0.9)]),
    )
    run = runtime.create_run(V3TaskConfig(target_language="zh", must_have_text=True))

    record = runtime.ingest_image(run.run_id, str(image))

    assert record.bucket == "rejected"
    assert record.reject_reason == "wrong_language"


def test_ingest_rejects_low_ocr_confidence_target_text(tmp_path):
    image = tmp_path / "low_confidence.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider([OcrTextBox(text="Start", bbox=[1, 2, 3, 4], confidence=0.31)]),
    )
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True, save_root=str(tmp_path / "runs")))

    record = runtime.ingest_image(run.run_id, str(image))

    assert record.bucket == "rejected"
    assert record.reject_reason == "low_ocr_confidence"


def test_ingest_rejects_unsafe_text(tmp_path):
    image = tmp_path / "unsafe.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider([OcrTextBox(text="Password required", bbox=[1, 2, 3, 4], confidence=0.95)]),
    )
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True, save_root=str(tmp_path / "runs")))

    record = runtime.ingest_image(run.run_id, str(image))

    assert record.bucket == "rejected"
    assert record.reject_reason == "unsafe_text"


def test_ingest_rejects_mixed_language_text(tmp_path):
    image = tmp_path / "mixed.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(text="Start", bbox=[0, 0, 10, 10], confidence=0.9),
                OcrTextBox(text="開始", bbox=[0, 20, 10, 30], confidence=0.9),
                OcrTextBox(text="시작", bbox=[0, 40, 10, 50], confidence=0.9),
            ]
        ),
    )
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True, save_root=str(tmp_path / "runs")))

    record = runtime.ingest_image(run.run_id, str(image))

    assert record.bucket == "rejected"
    assert record.reject_reason == "mixed_language"


def test_pc_app_ingest_accepts_dominant_target_language_with_ui_chrome_text(tmp_path):
    image = tmp_path / "notepadpp.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(
                    text="This is the first real software capture test. Start Next Settings Search View Encoding Language Preferences Find Replace Help Confirm Cancel",
                    bbox=[60, 100, 900, 240],
                    confidence=0.96,
                ),
                OcrTextBox(text="文件 编辑 搜索 视图 编码 语言 设置", bbox=[0, 30, 360, 52], confidence=0.91),
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

    record = runtime.ingest_image(run.run_id, str(image))

    assert record.bucket == "accepted"
    assert record.reject_reason is None


def test_ingest_ignores_low_confidence_short_language_noise(tmp_path):
    image = tmp_path / "english_with_noise.png"
    image.write_bytes(b"not-empty")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider(
            [
                OcrTextBox(text="Start", bbox=[0, 0, 10, 10], confidence=0.99),
                OcrTextBox(text="Пк", bbox=[20, 0, 30, 10], confidence=0.54),
            ]
        ),
    )
    run = runtime.create_run(V3TaskConfig(target_language="en", must_have_text=True, save_root=str(tmp_path / "runs")))

    record = runtime.ingest_image(run.run_id, str(image))

    assert record.bucket == "accepted"
    assert record.reject_reason is None


def test_action_after_capture_preserves_limited_duplicate_menu_state(tmp_path):
    image = tmp_path / "menu.png"
    image.write_bytes(b"same-frame")
    runtime = V3Runtime(
        store=V3RunStore(tmp_path / "runs"),
        ocr_provider=StaticOcrProvider([OcrTextBox(text="File Edit Search View Settings", bbox=[0, 0, 200, 20], confidence=0.95)]),
    )
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
        )
    )

    first = runtime.ingest_image(run.run_id, str(image), capture_reason="periodic", ui_state_hint="editor")
    periodic_duplicate = runtime.ingest_image(run.run_id, str(image), capture_reason="periodic", ui_state_hint="editor")
    preserved_1 = runtime.ingest_image(
        run.run_id,
        str(image),
        capture_reason="after_action",
        action_id="action:file",
        ui_state_hint="menu_file",
    )
    preserved_2 = runtime.ingest_image(
        run.run_id,
        str(image),
        capture_reason="menu_state",
        action_id="action:file",
        ui_state_hint="menu_file",
    )
    preserved_3 = runtime.ingest_image(
        run.run_id,
        str(image),
        capture_reason="after_action",
        action_id="action:file",
        ui_state_hint="menu_file",
    )
    capped = runtime.ingest_image(
        run.run_id,
        str(image),
        capture_reason="after_action",
        action_id="action:file",
        ui_state_hint="menu_file",
    )

    assert first.bucket == "accepted"
    assert periodic_duplicate.bucket == "rejected"
    assert periodic_duplicate.reject_reason == "near_duplicate"
    assert [preserved_1.bucket, preserved_2.bucket, preserved_3.bucket] == ["accepted", "accepted", "accepted"]
    assert capped.bucket == "rejected"
    assert capped.reject_reason == "near_duplicate"
    assert preserved_1.meta["capture_reason"] == "after_action"
    assert preserved_1.meta["ui_state_hint"] == "menu_file"
    assert periodic_duplicate.duplicate_decision["exact_duplicate"] is True
    assert periodic_duplicate.duplicate_decision["near_duplicate"] is True
    assert periodic_duplicate.duplicate_decision["duplicate_algorithm"] == "sha256_exact"
    assert periodic_duplicate.duplicate_decision["duplicate_decision_reason"] == "periodic_static_frame_rejected"
    assert periodic_duplicate.duplicate_decision["compared_with_image_id"] == first.image_id
    assert preserved_1.duplicate_decision["accepted_as_action_representative"] is True
    assert preserved_1.duplicate_decision["duplicate_decision_reason"] == "after_action_representative_accepted"
    assert preserved_1.duplicate_decision["representative_index"] == 1
    assert preserved_1.duplicate_decision["representative_limit"] == 3
    assert capped.duplicate_decision["representative_index"] == 4
    assert capped.duplicate_decision["representative_limit"] == 3


def test_preserved_action_duplicate_reuses_cached_ocr_result(tmp_path):
    image = tmp_path / "menu.png"
    image.write_bytes(b"same-frame")
    ocr_provider = StaticOcrProvider([OcrTextBox(text="File Edit Search View Settings", bbox=[0, 0, 200, 20], confidence=0.95)])
    runtime = V3Runtime(store=V3RunStore(tmp_path / "runs"), ocr_provider=ocr_provider)
    run = runtime.create_run(
        V3TaskConfig(
            app_type="pc_app",
            target_language="en",
            must_have_text=True,
            save_root=str(tmp_path / "runs"),
        )
    )

    first = runtime.ingest_image(
        run.run_id,
        str(image),
        capture_reason="after_action",
        action_id="action:file",
        ui_state_hint="menu_file",
    )
    preserved_duplicate = runtime.ingest_image(
        run.run_id,
        str(image),
        capture_reason="after_action",
        action_id="action:file",
        ui_state_hint="menu_file",
    )

    assert first.bucket == "accepted"
    assert preserved_duplicate.bucket == "accepted"
    assert preserved_duplicate.meta["ocr"]["provider"] == "static"
    assert preserved_duplicate.duplicate_decision["duplicate_decision_reason"] == "ocr_cache_hit_same_hash"
    assert ocr_provider.calls == 1
