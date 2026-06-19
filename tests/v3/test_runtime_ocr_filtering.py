from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import OcrResult, OcrTextBox, ProviderHealth, V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore


class StaticOcrProvider(OcrProvider):
    provider_name = "static"

    def __init__(self, boxes: list[OcrTextBox]) -> None:
        self.boxes = boxes

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=True)

    def recognize(self, image_path: str) -> OcrResult:
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
