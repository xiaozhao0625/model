import builtins
from types import SimpleNamespace

from ai_screenshot_platform.v3.ocr.paddle_provider import PaddleOcrProvider


class FakePaddleOCR:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def ocr(self, image_path, cls=True):
        return [
            [
                [
                    [[10, 20], [110, 20], [110, 60], [10, 60]],
                    ("Start", 0.96),
                ]
            ]
        ]


class FakePaddleOcr37:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def predict(self, image_path):
        return [
            {
                "rec_texts": ["Start Settings OK"],
                "rec_scores": [0.99],
                "rec_boxes": [[37, 84, 490, 142]],
            }
        ]


class FakePaddleOcr37NumpyBoxes:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def predict(self, image_path):
        import numpy as np

        return [
            {
                "rec_texts": ["Start Settings OK"],
                "rec_scores": [0.99],
                "rec_boxes": np.array([[37, 84, 490, 142]], dtype=np.int16),
            }
        ]


def test_paddle_provider_runs_real_inference_when_explicitly_enabled(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"fake")

    provider = PaddleOcrProvider(paddleocr_cls=FakePaddleOCR, enabled=True)
    result = provider.recognize(str(image))

    assert result.status == "ok"
    assert result.text_boxes[0].text == "Start"
    assert result.text_boxes[0].confidence == 0.96
    assert result.text_boxes[0].bbox == [10, 20, 110, 60]


def test_paddle_provider_passes_optional_ocr_version(monkeypatch, tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"fake")
    monkeypatch.setenv("APP_SHOT_PADDLEOCR_VERSION", "PP-OCRv5")

    provider = PaddleOcrProvider(paddleocr_cls=FakePaddleOCR, enabled=True)
    provider.recognize(str(image))

    assert provider._engine.kwargs["ocr_version"] == "PP-OCRv5"


def test_paddle_provider_uses_korean_engine_for_ko_target(tmp_path):
    image = tmp_path / "korean.png"
    image.write_bytes(b"fake")

    provider = PaddleOcrProvider(paddleocr_cls=FakePaddleOCR, enabled=True)
    provider.recognize_for_language(str(image), "ko")

    assert provider._engine.kwargs["lang"] == "korean"


def test_paddle_provider_keeps_distinct_engines_per_language(tmp_path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"fake")

    provider = PaddleOcrProvider(paddleocr_cls=FakePaddleOCR, enabled=True)
    provider.recognize_for_language(str(image), "en")
    english_engine = provider._engine
    provider.recognize_for_language(str(image), "ko")

    assert english_engine is not provider._engine
    assert provider._engine.kwargs["lang"] == "korean"


def test_paddle_provider_parses_paddleocr_37_mapping_results(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"fake")

    provider = PaddleOcrProvider(paddleocr_cls=FakePaddleOcr37, enabled=True)
    result = provider.recognize(str(image))

    assert result.status == "ok"
    assert result.text_boxes[0].text == "Start Settings OK"
    assert result.text_boxes[0].confidence == 0.99
    assert result.text_boxes[0].bbox == [37, 84, 490, 142]


def test_paddle_provider_parses_paddleocr_37_numpy_boxes(tmp_path):
    image = tmp_path / "english.png"
    image.write_bytes(b"fake")

    provider = PaddleOcrProvider(paddleocr_cls=FakePaddleOcr37NumpyBoxes, enabled=True)
    result = provider.recognize(str(image))

    assert result.status == "ok"
    assert result.text_boxes[0].bbox == [37, 84, 490, 142]


def test_paddle_provider_stays_disabled_by_default_when_available():
    provider = PaddleOcrProvider(paddleocr_cls=FakePaddleOCR)

    assert provider.health().status == "ready"
    assert provider.health().enabled is False
    assert provider.recognize("unused.png").status == "unavailable"


def test_paddle_provider_configures_mkldnn_before_import(monkeypatch):
    captured: dict[str, str | None] = {}
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "paddleocr":
            import os

            captured["mkldnn"] = os.environ.get("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT")
            return SimpleNamespace(PaddleOCR=FakePaddleOCR)
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.delenv("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    PaddleOcrProvider()

    assert captured["mkldnn"] == "False"
