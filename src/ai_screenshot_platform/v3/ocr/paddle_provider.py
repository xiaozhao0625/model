from __future__ import annotations

import os
import numbers
from collections.abc import Mapping
from typing import Any

from ai_screenshot_platform.v3.ocr.base import OcrProvider
from ai_screenshot_platform.v3.schemas import OcrResult, OcrTextBox, ProviderHealth


class PaddleOcrProvider(OcrProvider):
    provider_name = "paddleocr"

    def __init__(self, paddleocr_cls: type[Any] | None = None, enabled: bool | None = None) -> None:
        self._paddleocr_cls = paddleocr_cls
        self._enabled = _env_enabled("APP_SHOT_ENABLE_PADDLEOCR") if enabled is None else enabled
        self._engine: Any | None = None
        self._engines: dict[str, Any] = {}
        self._error: str | None = None
        if self._paddleocr_cls is not None:
            return

        try:
            from paddleocr import PaddleOCR  # type: ignore
            self._paddleocr_cls = PaddleOCR
        except Exception as exc:  # Optional runtime dependency.
            self._error = str(exc)

    def health(self) -> ProviderHealth:
        if self._paddleocr_cls is None:
            return ProviderHealth(
                provider=self.provider_name,
                status="unavailable",
                enabled=False,
                reason="paddleocr_not_installed",
                details={"error": self._error},
            )
        return ProviderHealth(
            provider=self.provider_name,
            status="ready",
            enabled=self._enabled,
            reason="enabled" if self._enabled else "available_but_disabled_by_default",
        )

    def recognize(self, image_path: str) -> OcrResult:
        return self._recognize_with_lang(image_path, os.environ.get("APP_SHOT_PADDLEOCR_LANG", "ch"))

    def recognize_for_language(self, image_path: str, target_language: str) -> OcrResult:
        return self._recognize_with_lang(image_path, _paddle_lang_for_target(target_language))

    def _recognize_with_lang(self, image_path: str, lang: str) -> OcrResult:
        if self._paddleocr_cls is None:
            return OcrResult(provider=self.provider_name, status="unavailable", error="paddleocr_not_installed")
        if not self._enabled:
            return OcrResult(provider=self.provider_name, status="unavailable", error="paddleocr_disabled_by_default")

        try:
            engine = self._get_engine(lang)
            raw = engine.predict(image_path) if hasattr(engine, "predict") else engine.ocr(image_path, cls=True)
            return OcrResult(provider=self.provider_name, status="ok", text_boxes=_parse_paddle_result(raw))
        except Exception as exc:
            return OcrResult(provider=self.provider_name, status="error", error=str(exc))

    def _get_engine(self, lang: str | None = None) -> Any:
        lang = lang or os.environ.get("APP_SHOT_PADDLEOCR_LANG", "ch")
        if lang in self._engines:
            self._engine = self._engines[lang]
            return self._engine
        _configure_paddle_cache_env()
        ocr_version = os.environ.get("APP_SHOT_PADDLEOCR_VERSION")
        try:
            self._engine = self._paddleocr_cls(
                use_textline_orientation=False,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                lang=lang,
                ocr_version=ocr_version,
            )
        except TypeError:
            self._engine = self._paddleocr_cls(lang=lang)
        self._engines[lang] = self._engine
        return self._engine


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _configure_paddle_cache_env() -> None:
    default_root = os.environ.get("APP_SHOT_MODELS")
    if default_root:
        os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(os.path.join(default_root, "paddleocr", "paddlex")))
    os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "modelscope")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
    app_shot_home = os.environ.get("APP_SHOT_HOME")
    if app_shot_home:
        os.environ.setdefault("PADDLE_HOME", str(os.path.join(app_shot_home, "cache", "paddle")))


def _paddle_lang_for_target(target_language: str) -> str:
    if target_language.startswith("ko"):
        return "korean"
    if target_language.startswith("ja"):
        return os.environ.get("APP_SHOT_PADDLEOCR_LANG_JA", os.environ.get("APP_SHOT_PADDLEOCR_LANG", "ch"))
    if target_language.startswith("en"):
        return os.environ.get("APP_SHOT_PADDLEOCR_LANG_EN", os.environ.get("APP_SHOT_PADDLEOCR_LANG", "ch"))
    return os.environ.get("APP_SHOT_PADDLEOCR_LANG", "ch")


def _parse_paddle_result(raw: Any) -> list[OcrTextBox]:
    if isinstance(raw, Mapping):
        texts = raw.get("rec_texts") or []
        scores = raw.get("rec_scores") or []
        boxes = raw.get("rec_boxes")
        if boxes is None:
            boxes = raw.get("dt_polys")
        if boxes is None:
            boxes = []
        return [
            OcrTextBox(text=str(text), bbox=_bbox_from_points(box), confidence=float(scores[index] if index < len(scores) else 0.0))
            for index, (text, box) in enumerate(zip(texts, boxes))
        ]

    boxes: list[OcrTextBox] = []
    if isinstance(raw, (list, tuple)):
        for item in raw:
            if isinstance(item, Mapping):
                boxes.extend(_parse_paddle_result(item))
        if boxes:
            return boxes

    for line in _iter_paddle_lines(raw):
        if not (isinstance(line, (list, tuple)) and len(line) >= 2):
            continue
        bbox_raw, text_raw = line[0], line[1]
        if isinstance(text_raw, (list, tuple)) and len(text_raw) >= 2:
            text = str(text_raw[0])
            confidence = float(text_raw[1])
        else:
            text = str(text_raw)
            confidence = 0.0
        boxes.append(OcrTextBox(text=text, bbox=_bbox_from_points(bbox_raw), confidence=confidence))
    return boxes


def _iter_paddle_lines(raw: Any):
    if raw is None:
        return
    if isinstance(raw, (list, tuple)):
        if len(raw) >= 2 and _looks_like_bbox(raw[0]):
            yield raw
            return
        for item in raw:
            yield from _iter_paddle_lines(item)


def _looks_like_bbox(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and bool(value) and isinstance(value[0], (list, tuple))


def _bbox_from_points(points: Any) -> list[int]:
    if hasattr(points, "tolist"):
        points = points.tolist()
    if isinstance(points, (list, tuple)) and len(points) == 4 and all(isinstance(item, numbers.Real) for item in points):
        return [int(float(item)) for item in points]
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
