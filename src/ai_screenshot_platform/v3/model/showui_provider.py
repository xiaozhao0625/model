from __future__ import annotations

import ast
import importlib
import os
import re
from pathlib import Path
from typing import Protocol

from PIL import Image

from ai_screenshot_platform.v3.model.base import UiModelProvider
from ai_screenshot_platform.v3.model.prompt_templates import SHOWUI_RANK_PROMPT
from ai_screenshot_platform.v3.schemas import ModelClickCandidate, ModelRequest, ModelResult, ProviderHealth


class ShowUiRunner(Protocol):
    def run(self, image_path: str, query: str) -> str:
        raise NotImplementedError


class ShowUiProvider(UiModelProvider):
    provider_name = "showui"

    def __init__(self, model_dir: str | None = None, enabled: bool | None = None, runner: ShowUiRunner | None = None) -> None:
        self.model_dir = Path(model_dir) if model_dir is not None else _default_showui_dir()
        self.enabled = _showui_enabled() if enabled is None else enabled
        self.runner = runner

    def health(self) -> ProviderHealth:
        if not self.model_dir.exists():
            return ProviderHealth(
                provider=self.provider_name,
                status="unavailable",
                enabled=False,
                reason="showui_weights_missing",
                details={"model_dir": str(self.model_dir)},
            )
        return ProviderHealth(
            provider=self.provider_name,
            status="degraded" if not self.enabled else "ready",
            enabled=self.enabled,
            reason="weights_present_but_disabled" if not self.enabled else "enabled",
            details={"model_dir": str(self.model_dir)},
        )

    def classify_scene(self, request: ModelRequest) -> ModelResult:
        return self._unavailable_result()

    def propose_visual_candidates(self, request: ModelRequest) -> ModelResult:
        return self._unavailable_result()

    def rank_click_candidates(self, request: ModelRequest) -> ModelResult:
        health = self.health()
        if health.status != "ready" or not health.enabled:
            return self._unavailable_result()
        try:
            runner = self.runner or LocalShowUiRunner(self.model_dir)
            output = runner.run(request.screenshot_path, _rank_query(request))
            point = parse_showui_point(output)
            if point is None:
                return ModelResult(provider=self.provider_name, status="error", error="showui_point_parse_failed")
            candidate = _candidate_from_point(request.screenshot_path, point, _label_from_output(output) or _label_from_request(request))
            return ModelResult(provider=self.provider_name, status="ok", candidates=[candidate])
        except Exception as exc:  # pragma: no cover - real model failures are environment-specific
            return ModelResult(provider=self.provider_name, status="error", error=str(exc))

    def _unavailable_result(self) -> ModelResult:
        health = self.health()
        return ModelResult(provider=self.provider_name, status=_model_status_from_health(health), error=health.reason)


class LocalShowUiRunner:
    def __init__(self, model_dir: Path) -> None:
        self.model_dir = model_dir
        self._model = None
        self._processor = None

    def run(self, image_path: str, query: str) -> str:
        model, processor = self._load()
        min_pixels = 256 * 28 * 28
        max_pixels = 1344 * 28 * 28
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SHOWUI_RANK_PROMPT},
                    {"type": "image", "image": image_path, "min_pixels": min_pixels, "max_pixels": max_pixels},
                    {"type": "text", "text": query},
                ],
            }
        ]
        import torch
        from qwen_vl_utils import process_vision_info

        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt")
        inputs = inputs.to("cuda" if torch.cuda.is_available() else "cpu")
        generated_ids = model.generate(**inputs, max_new_tokens=128)
        generated_ids_trimmed = [out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        return processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]

    def _load(self):
        if self._model is not None and self._processor is not None:
            return self._model, self._processor
        import torch
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        kwargs = {"local_files_only": True}
        if torch.cuda.is_available():
            kwargs.update({"torch_dtype": torch.bfloat16, "device_map": "auto"})
        model = Qwen2VLForConditionalGeneration.from_pretrained(str(self.model_dir), **kwargs)
        if not torch.cuda.is_available():
            model = model.to("cpu")
        processor = AutoProcessor.from_pretrained(
            str(self.model_dir),
            min_pixels=256 * 28 * 28,
            max_pixels=1344 * 28 * 28,
            local_files_only=True,
        )
        self._model = model
        self._processor = processor
        return model, processor


def parse_showui_point(output: str) -> tuple[float, float] | None:
    parsed = _literal_or_none(output.strip().rstrip(","))
    point = _point_from_literal(parsed)
    if point is None:
        point = _point_from_regex(output)
    if point is None:
        return None
    x, y = point
    if 1 < x <= 100 and 1 < y <= 100:
        x = x / 100
        y = y / 100
    if 0 <= x <= 1 and 0 <= y <= 1:
        return (x, y)
    return None


def _literal_or_none(value: str):
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return None


def _point_from_literal(value) -> tuple[float, float] | None:
    if isinstance(value, dict):
        for key in ("position", "point", "coordinate", "coordinates"):
            point = _point_from_literal(value.get(key))
            if point is not None:
                return point
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        first = value[0]
        if isinstance(first, (list, tuple)):
            return _point_from_literal(first)
        try:
            return (float(value[0]), float(value[1]))
        except (TypeError, ValueError):
            return None
    return None


def _point_from_regex(output: str) -> tuple[float, float] | None:
    match = re.search(r"[-+]?(?:\d*\.\d+|\d+)\s*,\s*[-+]?(?:\d*\.\d+|\d+)", output)
    if not match:
        return None
    left, right = match.group(0).split(",", 1)
    return (float(left), float(right))


def _label_from_output(output: str) -> str | None:
    parsed = _literal_or_none(output.strip().rstrip(","))
    if isinstance(parsed, dict) and parsed.get("value"):
        return str(parsed["value"])
    return None


def _label_from_request(request: ModelRequest) -> str:
    for key in ("goal", "instruction", "task", "app_name"):
        value = request.task_context.get(key)
        if value:
            return str(value)
    return "showui_click"


def _candidate_from_point(image_path: str, point: tuple[float, float], label: str) -> ModelClickCandidate:
    with Image.open(image_path) as image:
        width, height = image.size
    click_x = round(point[0] * width)
    click_y = round(point[1] * height)
    half = 20
    return ModelClickCandidate(
        label=label,
        source="showui",
        bbox=[
            max(0, click_x - half),
            max(0, click_y - half),
            min(width, click_x + half),
            min(height, click_y + half),
        ],
        click_x=click_x,
        click_y=click_y,
        confidence=0.75,
        reason="showui_grounding",
    )


def _rank_query(request: ModelRequest) -> str:
    goal = _label_from_request(request)
    ocr_text = ", ".join(box.text for box in request.ocr_boxes[:8])
    if ocr_text:
        return f"Find the safest clickable location for: {goal}. OCR text: {ocr_text}"
    return f"Find the safest clickable location for: {goal}."


def _default_showui_dir() -> Path:
    explicit = os.environ.get("APP_SHOT_SHOWUI_MODEL_DIR")
    if explicit:
        return Path(explicit)
    model_root = os.environ.get("APP_SHOT_MODELS")
    if model_root:
        return Path(model_root) / "showui" / "ShowUI-2B"
    return Path("models/showui")


def _showui_enabled() -> bool:
    return os.environ.get("APP_SHOT_ENABLE_SHOWUI", "").lower() in {"1", "true", "yes", "on"}


def _model_status_from_health(health: ProviderHealth) -> str:
    return "degraded" if health.status == "ready" else health.status


def preload_showui_torch_runtime(importer=importlib.import_module) -> None:
    if _showui_enabled():
        importer("torch")
