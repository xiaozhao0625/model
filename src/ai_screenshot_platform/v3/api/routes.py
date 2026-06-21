from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import ModelRequest, V3ActionAuditRequest, V3ImageIngestRequest, V3RunCreateRequest


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
        return v3_ok([_image_payload(image) for image in get_runtime(request).images(run_id)])

    @router.get("/runs/{run_id}/images/{image_id}/thumbnail")
    def image_thumbnail(run_id: str, image_id: str, request: Request):
        image = _find_image(get_runtime(request), run_id, image_id)
        return FileResponse(_image_file(image), media_type="image/png")

    @router.get("/runs/{run_id}/images/{image_id}/preview")
    def image_preview(run_id: str, image_id: str, request: Request):
        image = _find_image(get_runtime(request), run_id, image_id)
        return FileResponse(_image_file(image), media_type="image/png")

    @router.post("/runs/{run_id}/images/{image_id}/reveal")
    def reveal_image(run_id: str, image_id: str, request: Request, dry_run: bool = False):
        image = _find_image(get_runtime(request), run_id, image_id)
        path = _image_file(image)
        folder = path.parent
        status = "dry_run" if dry_run else _open_in_file_manager(folder, select_path=path)
        return v3_ok({"status": status, "path": str(path), "folder": str(folder)})

    @router.post("/runs/{run_id}/images/ingest")
    def ingest_image(run_id: str, payload: V3ImageIngestRequest, request: Request):
        return v3_ok(
            get_runtime(request)
            .ingest_image(
                run_id,
                payload.image_path,
                capture_reason=payload.capture_reason,
                action_id=payload.action_id,
                ui_state_hint=payload.ui_state_hint,
            )
            .model_dump()
        )

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
        return v3_ok(get_runtime(request).list_actions(run_id))

    @router.post("/runs/{run_id}/actions/evaluate")
    def evaluate_action(run_id: str, request: Request):
        return v3_ok(get_runtime(request).evaluate_action(run_id))

    @router.post("/runs/{run_id}/actions/execute")
    def execute_action(run_id: str, request: Request):
        return v3_ok(get_runtime(request).execute_action(run_id))

    @router.post("/runs/{run_id}/actions/record")
    def record_action(run_id: str, payload: V3ActionAuditRequest, request: Request):
        return v3_ok(get_runtime(request).record_action_audit(run_id, payload.action))

    @router.get("/action/health")
    def action_health(request: Request):
        return v3_ok(get_runtime(request).action_health())

    @router.get("/runs/{run_id}/events")
    def events(run_id: str, request: Request):
        return v3_ok([event.model_dump() for event in get_runtime(request).events(run_id)])

    @router.post("/runs/{run_id}/open-folder")
    def open_folder(run_id: str, request: Request, dry_run: bool = False):
        runtime = get_runtime(request)
        path = runtime.store.run_dir(run_id).resolve()
        status = "dry_run" if dry_run else _open_in_file_manager(path)
        return v3_ok({"status": status, "path": str(path)})

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


def _image_payload(image) -> dict[str, object]:
    payload = image.model_dump()
    path = Path(image.path).resolve()
    payload["absolute_path"] = str(path)
    payload["folder"] = str(path.parent)
    return payload


def _find_image(runtime: V3Runtime, run_id: str, image_id: str):
    for image in runtime.images(run_id):
        if image.image_id == image_id:
            return image
    raise HTTPException(status_code=404, detail=f"image not found: {image_id}")


def _image_file(image) -> Path:
    path = Path(image.path).resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"image file not found: {path}")
    return path


def _open_in_file_manager(folder: Path, select_path: Path | None = None) -> str:
    if os.environ.get("APP_SHOT_DISABLE_OPEN_FOLDER") == "1":
        return "disabled_by_env"
    try:
        if os.name == "nt":
            if select_path is not None:
                subprocess.Popen(["explorer", f"/select,{select_path}"])
            else:
                os.startfile(str(folder))  # type: ignore[attr-defined]
            return "opened"
        subprocess.Popen(["xdg-open", str(folder)])
        return "opened"
    except Exception as exc:  # pragma: no cover - OS integration varies.
        return f"open_failed:{exc}"
