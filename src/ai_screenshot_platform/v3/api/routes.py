from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request

from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import ModelRequest, V3ImageIngestRequest, V3RunCreateRequest


def v3_ok(data: object) -> dict[str, object]:
    return {"ok": True, "data": data, "error": None}


def get_runtime(request: Request) -> V3Runtime:
    runtime = getattr(request.app.state, "v3_runtime", None)
    if runtime is None:
        runtime = V3Runtime()
        request.app.state.v3_runtime = runtime
    return runtime


def create_v3_router() -> APIRouter:
    router = APIRouter(prefix="/api/v3", tags=["v3"])

    @router.get("/health")
    def health(request: Request):
        return v3_ok(get_runtime(request).health().model_dump())

    @router.get("/config/defaults")
    def defaults(request: Request):
        return v3_ok(get_runtime(request).defaults().model_dump())

    @router.post("/runs")
    def create_run(payload: V3RunCreateRequest, request: Request):
        return v3_ok(get_runtime(request).create_run(payload.config).model_dump())

    @router.get("/runs")
    def list_runs(request: Request):
        return v3_ok([record.model_dump() for record in get_runtime(request).list_runs()])

    @router.get("/runs/{run_id}")
    def get_run(run_id: str, request: Request):
        return v3_ok(get_runtime(request).get_run(run_id).model_dump())

    @router.post("/runs/{run_id}/start")
    def start_run(run_id: str, request: Request):
        return v3_ok(get_runtime(request).start_run(run_id).model_dump())

    @router.post("/runs/{run_id}/pause")
    def pause_run(run_id: str, request: Request):
        return v3_ok(get_runtime(request).pause_run(run_id).model_dump())

    @router.post("/runs/{run_id}/stop")
    def stop_run(run_id: str, request: Request):
        return v3_ok(get_runtime(request).stop_run(run_id).model_dump())

    @router.get("/runs/{run_id}/summary")
    def summary(run_id: str, request: Request):
        return v3_ok(get_runtime(request).summary(run_id).model_dump())

    @router.get("/runs/{run_id}/images")
    def images(run_id: str, request: Request):
        return v3_ok([image.model_dump() for image in get_runtime(request).images(run_id)])

    @router.post("/runs/{run_id}/images/ingest")
    def ingest_image(run_id: str, payload: V3ImageIngestRequest, request: Request):
        return v3_ok(get_runtime(request).ingest_image(run_id, payload.image_path).model_dump())

    @router.get("/runs/{run_id}/ocr-status")
    def ocr_status(run_id: str, request: Request):
        return v3_ok(get_runtime(request).ocr_status(run_id))

    @router.get("/runs/{run_id}/model-status")
    def model_status(run_id: str, request: Request):
        return v3_ok(get_runtime(request).model_status(run_id))

    @router.get("/runs/{run_id}/candidates")
    def candidates(run_id: str, request: Request):
        return v3_ok(get_runtime(request).candidates(run_id))

    @router.get("/runs/{run_id}/actions")
    def actions(run_id: str, request: Request):
        return v3_ok(get_runtime(request).actions_for_run(run_id))

    @router.get("/runs/{run_id}/events")
    def events(run_id: str, request: Request):
        return v3_ok([event.model_dump() for event in get_runtime(request).events(run_id)])

    @router.post("/runs/{run_id}/open-folder")
    def open_folder(run_id: str, request: Request):
        runtime = get_runtime(request)
        run = runtime.get_run(run_id)
        return v3_ok({"status": "not_opened_in_api", "path": f"{run.config.save_root}/{run.run_id}"})

    @router.post("/runs/{run_id}/delete-rejected")
    def delete_rejected(run_id: str, request: Request):
        get_runtime(request).store.append_event(run_id, "delete_rejected_requested", {"executed": False})
        return v3_ok({"executed": False, "reason": "delete_rejected_disabled_by_default"})

    @router.get("/model/providers")
    def model_providers(request: Request):
        return v3_ok(get_runtime(request).model_status("_providers")["providers"])

    @router.get("/model/health")
    def model_health(request: Request):
        return v3_ok(get_runtime(request).health().model_dump())

    @router.post("/model/classify-scene")
    def model_classify_scene(payload: ModelRequest, request: Request):
        return v3_ok(get_runtime(request).model_classify_scene(payload).model_dump())

    @router.post("/model/rank-click-candidates")
    def model_rank_click_candidates(payload: ModelRequest, request: Request):
        return v3_ok(get_runtime(request).model_rank_click_candidates(payload).model_dump())

    @router.post("/model/propose-visual-candidates")
    def model_propose_visual_candidates(payload: ModelRequest, request: Request):
        return v3_ok(get_runtime(request).model_propose_visual_candidates(payload).model_dump())

    return router


def register_v3_routes(app: FastAPI) -> None:
    app.include_router(create_v3_router())
