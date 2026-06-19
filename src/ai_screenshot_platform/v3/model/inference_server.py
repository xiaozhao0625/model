from __future__ import annotations

from fastapi import FastAPI

from ai_screenshot_platform.v3.model.health import build_v3_health
from ai_screenshot_platform.v3.model.registry import UiModelRegistry
from ai_screenshot_platform.v3.schemas import ModelRequest


def create_v3_model_server() -> FastAPI:
    app = FastAPI(title="V3 Local UI Model Server")
    registry = UiModelRegistry()

    @app.get("/health")
    def health():
        return {"ok": True, "data": build_v3_health(registry).model_dump(), "error": None}

    @app.post("/classify-scene")
    def classify_scene(payload: ModelRequest):
        return {"ok": True, "data": registry.classify_scene(payload).model_dump(), "error": None}

    @app.post("/rank-click-candidates")
    def rank_click_candidates(payload: ModelRequest):
        return {"ok": True, "data": registry.rank_click_candidates(payload).model_dump(), "error": None}

    @app.post("/propose-visual-candidates")
    def propose_visual_candidates(payload: ModelRequest):
        return {"ok": True, "data": registry.propose_visual_candidates(payload).model_dump(), "error": None}

    return app
