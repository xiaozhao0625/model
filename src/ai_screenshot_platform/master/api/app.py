from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ai_screenshot_platform.common.model_gateway.contracts import (
    GroundRequest,
    SceneClassifyRequest,
)
from ai_screenshot_platform.master.core.config import MasterSettings
from ai_screenshot_platform.master.core.deps import MemoryRedisClient
from ai_screenshot_platform.master.core.response import error, ok
from ai_screenshot_platform.master.repositories.app_repo import AppRepo
from ai_screenshot_platform.master.repositories.database import MasterDatabase
from ai_screenshot_platform.master.repositories.image_repo import ImageRepo
from ai_screenshot_platform.master.repositories.production_readiness_repo import (
    ProductionReadinessRepo,
)
from ai_screenshot_platform.master.repositories.run_repo import RunRepo
from ai_screenshot_platform.master.repositories.upload_repo import UploadRepo
from ai_screenshot_platform.master.repositories.worker_repo import WorkerRepo
from ai_screenshot_platform.master.schemas.api import (
    ActApiRequest,
    AppCreateRequest,
    BehaviorCandidateIngestRequest,
    BehaviorCandidateReviewRequest,
    DiagnosticIngestRequest,
    GroundApiRequest,
    OcrReportIngestRequest,
    QualityReportIngestRequest,
    RunCreateRequest,
    SceneClassifyApiRequest,
    ToolHealthIngestRequest,
    UploadRunRequest,
    WorkerRegisterRequest,
    WorkerResultReportRequest,
)
from ai_screenshot_platform.master.services.app_service import AppService
from ai_screenshot_platform.master.services.model_gateway_service import (
    ModelGatewayProxyService,
)
from ai_screenshot_platform.master.services.production_readiness_service import (
    ProductionReadinessService,
)
from ai_screenshot_platform.master.services.run_service import RunService
from ai_screenshot_platform.master.services.serialization import to_api_data
from ai_screenshot_platform.master.services.upload_service import UploadService
from ai_screenshot_platform.master.services.worker_service import WorkerService


@dataclass
class MasterServices:
    app_service: AppService
    run_service: RunService
    worker_service: WorkerService
    upload_service: UploadService
    model_gateway_service: ModelGatewayProxyService
    production_readiness_service: ProductionReadinessService
    image_repo: ImageRepo
    redis_client: MemoryRedisClient


def create_app(settings: MasterSettings | None = None) -> FastAPI:
    settings = settings or MasterSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = MasterDatabase(settings)
        app.state.database = database
        app.state.services = _create_services(settings, database)
        try:
            yield
        finally:
            database.close()

    app = FastAPI(title="AI Screenshot Platform Master API", lifespan=lifespan)
    app.state.settings = settings
    app.state.database = None
    app.state.services = None

    def get_services() -> MasterServices:
        services = app.state.services
        if services is None:
            raise ValueError("master services are not initialized")
        return services

    @app.exception_handler(KeyError)
    async def key_error_handler(_, exc: KeyError):
        return JSONResponse(status_code=404, content=error(str(exc)))

    @app.exception_handler(ValueError)
    async def value_error_handler(_, exc: ValueError):
        return JSONResponse(status_code=400, content=error(str(exc)))

    @app.get("/health")
    def health():
        return ok(
            {
                "status": "ok",
                "env": settings.env,
                "database_backend": settings.database_backend,
            }
        )

    @app.post("/api/apps")
    def create_app_record(payload: AppCreateRequest):
        services = get_services()
        return ok(
            to_api_data(
                services.app_service.create(
                    app_id=payload.app_id,
                    name=payload.name,
                    type=payload.type,
                    platform=payload.platform,
                )
            )
        )

    @app.get("/api/apps")
    def list_apps():
        return ok(to_api_data(get_services().app_service.list()))

    @app.get("/api/apps/{app_id}")
    def get_app_record(app_id: str):
        return ok(to_api_data(get_services().app_service.get(app_id)))

    @app.post("/api/runs")
    def create_run(payload: RunCreateRequest):
        return ok(
            to_api_data(
                get_services().run_service.create_run(
                    run_id=payload.run_id,
                    app_id=payload.app_id,
                    target_min=payload.target_min,
                    target_max=payload.target_max,
                )
            )
        )

    @app.get("/api/runs")
    def list_runs():
        return ok(to_api_data(get_services().run_service.list()))

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        return ok(to_api_data(get_services().run_service.get(run_id)))

    @app.post("/api/runs/{run_id}/start")
    def start_run(run_id: str):
        return ok(to_api_data(get_services().run_service.start_run(run_id)))

    @app.get("/api/runs/{run_id}/summary")
    def get_run_summary(run_id: str):
        return ok(get_services().run_service.summary(run_id))

    @app.post("/api/workers/register")
    def register_worker(payload: WorkerRegisterRequest):
        return ok(
            to_api_data(
                get_services().worker_service.register(
                    worker_id=payload.worker_id,
                    type=payload.type,
                    machine_name=payload.machine_name,
                    capabilities=payload.capabilities,
                )
            )
        )

    @app.get("/api/workers")
    def list_workers():
        return ok(to_api_data(get_services().worker_service.list()))

    @app.post("/api/workers/{worker_id}/heartbeat")
    def worker_heartbeat(worker_id: str):
        services = get_services()
        worker = services.worker_service.heartbeat(worker_id)
        services.redis_client.set(f"worker:{worker_id}:heartbeat", worker.heartbeat)
        return ok(to_api_data(worker))

    @app.post("/api/workers/{worker_id}/claim")
    def worker_claim(worker_id: str):
        return ok(to_api_data(get_services().worker_service.claim(worker_id)))

    @app.post("/api/workers/{worker_id}/runs/{run_id}/report")
    def worker_report(worker_id: str, run_id: str, payload: WorkerResultReportRequest):
        if payload.run_id != run_id:
            raise ValueError("payload run_id must match route run_id")
        result = get_services().worker_service.report(
            worker_id=worker_id,
            run_id=run_id,
            result=payload,
        )
        return ok(to_api_data(result))

    @app.post("/api/upload-manifest")
    def upload_manifest(payload: UploadRunRequest):
        return ok(to_api_data(get_services().upload_service.manifest(payload.run_id)))

    @app.post("/api/confirm-upload")
    def confirm_upload(payload: UploadRunRequest):
        return ok(to_api_data(get_services().upload_service.confirm(payload.run_id)))

    @app.post("/api/cleanup")
    def cleanup(payload: UploadRunRequest):
        return ok(to_api_data(get_services().upload_service.cleanup(payload.run_id)))

    @app.post("/api/finalize")
    def finalize(payload: UploadRunRequest):
        return ok(to_api_data(get_services().upload_service.finalize(payload.run_id)))

    @app.post("/api/runs/{run_id}/upload-manifest")
    def run_upload_manifest(run_id: str):
        return ok(to_api_data(get_services().upload_service.manifest(run_id)))

    @app.post("/api/runs/{run_id}/confirm-upload")
    def run_confirm_upload(run_id: str):
        return ok(to_api_data(get_services().upload_service.confirm(run_id)))

    @app.post("/api/runs/{run_id}/cleanup")
    def run_cleanup(run_id: str):
        return ok(to_api_data(get_services().upload_service.cleanup(run_id)))

    @app.post("/api/runs/{run_id}/finalize")
    def run_finalize(run_id: str):
        return ok(to_api_data(get_services().upload_service.finalize(run_id)))

    @app.post("/api/model/scene_classify")
    def scene_classify(payload: SceneClassifyApiRequest):
        result = get_services().model_gateway_service.scene_classify(
            SceneClassifyRequest(
                app_id=payload.app_id,
                run_id=payload.run_id,
                screenshot_path=payload.screenshot_path,
                context=payload.context,
            )
        )
        return ok(to_api_data(result))

    @app.post("/api/model/ground")
    def ground(payload: GroundApiRequest):
        result = get_services().model_gateway_service.ground(
            GroundRequest(
                app_id=payload.app_id,
                run_id=payload.run_id,
                screenshot_path=payload.screenshot_path,
                target_description=payload.target_description,
                context=payload.context,
            )
        )
        return ok(to_api_data(result))

    @app.post("/api/model/act")
    def act(payload: ActApiRequest):
        result = get_services().model_gateway_service.act(
            app_id=payload.app_id,
            run_id=payload.run_id,
            screenshot_path=payload.screenshot_path,
            scene_class=payload.scene_class,
            instruction=payload.instruction,
            target_description=payload.target_description,
            context=payload.context,
        )
        return ok(to_api_data(result))

    @app.get("/api/quality-reports")
    def list_quality_reports():
        return ok(to_api_data(get_services().production_readiness_service.list_quality_reports()))

    @app.get("/api/quality-reports/{run_id}")
    def get_quality_report(run_id: str):
        return ok(to_api_data(get_services().production_readiness_service.get_quality_report(run_id)))

    @app.post("/api/quality-reports/ingest")
    def ingest_quality_report(payload: QualityReportIngestRequest):
        return ok(
            to_api_data(
                get_services().production_readiness_service.ingest_quality_report(
                    payload.model_dump()
                )
            )
        )

    @app.get("/api/ocr/status")
    def get_ocr_status():
        return ok(to_api_data(get_services().production_readiness_service.latest_ocr_status()))

    @app.get("/api/ocr/reports")
    def list_ocr_reports():
        return ok(to_api_data(get_services().production_readiness_service.list_ocr_reports()))

    @app.get("/api/ocr/reports/{run_id}")
    def get_ocr_report(run_id: str):
        return ok(to_api_data(get_services().production_readiness_service.get_ocr_report(run_id)))

    @app.post("/api/ocr/reports/ingest")
    def ingest_ocr_report(payload: OcrReportIngestRequest):
        return ok(
            to_api_data(
                get_services().production_readiness_service.ingest_ocr_report(
                    payload.model_dump()
                )
            )
        )

    @app.get("/api/tool-health")
    def get_tool_health():
        return ok(to_api_data(get_services().production_readiness_service.tool_health()))

    @app.get("/api/tool-health/workers")
    def get_worker_tool_health():
        return ok(to_api_data(get_services().production_readiness_service.worker_tool_health()))

    @app.get("/api/tool-health/android")
    def get_android_tool_health():
        return ok(to_api_data(get_services().production_readiness_service.android_tool_health()))

    @app.post("/api/tool-health/ingest")
    def ingest_tool_health(payload: ToolHealthIngestRequest):
        return ok(
            to_api_data(
                get_services().production_readiness_service.ingest_tool_health(
                    payload.model_dump()
                )
            )
        )

    @app.get("/api/behavior-candidates")
    def list_behavior_candidates():
        return ok(to_api_data(get_services().production_readiness_service.list_behavior_candidates()))

    @app.get("/api/behavior-candidates/{candidate_pack_id}")
    def get_behavior_candidate(candidate_pack_id: str):
        return ok(
            to_api_data(
                get_services().production_readiness_service.get_behavior_candidate(
                    candidate_pack_id
                )
            )
        )

    @app.post("/api/behavior-candidates/ingest")
    def ingest_behavior_candidate(payload: BehaviorCandidateIngestRequest):
        return ok(
            to_api_data(
                get_services().production_readiness_service.ingest_behavior_candidate(
                    payload.model_dump()
                )
            )
        )

    @app.post("/api/behavior-candidates/{candidate_pack_id}/approve")
    def approve_behavior_candidate(
        candidate_pack_id: str, payload: BehaviorCandidateReviewRequest | None = None
    ):
        payload = payload or BehaviorCandidateReviewRequest()
        return ok(
            to_api_data(
                get_services().production_readiness_service.approve_behavior_candidate(
                    candidate_pack_id,
                    reviewer=payload.reviewer,
                    reason=payload.reason,
                )
            )
        )

    @app.post("/api/behavior-candidates/{candidate_pack_id}/reject")
    def reject_behavior_candidate(
        candidate_pack_id: str, payload: BehaviorCandidateReviewRequest | None = None
    ):
        payload = payload or BehaviorCandidateReviewRequest()
        return ok(
            to_api_data(
                get_services().production_readiness_service.reject_behavior_candidate(
                    candidate_pack_id,
                    reviewer=payload.reviewer,
                    reason=payload.reason,
                )
            )
        )

    @app.post("/api/behavior-candidates/{candidate_pack_id}/rollback")
    def rollback_behavior_candidate(
        candidate_pack_id: str, payload: BehaviorCandidateReviewRequest | None = None
    ):
        payload = payload or BehaviorCandidateReviewRequest()
        return ok(
            to_api_data(
                get_services().production_readiness_service.rollback_behavior_candidate(
                    candidate_pack_id,
                    reviewer=payload.reviewer,
                    reason=payload.reason,
                )
            )
        )

    @app.get("/api/diagnostics")
    def list_diagnostics():
        return ok(to_api_data(get_services().production_readiness_service.list_diagnostics()))

    @app.post("/api/diagnostics/ingest")
    def ingest_diagnostic(payload: DiagnosticIngestRequest):
        return ok(
            to_api_data(
                get_services().production_readiness_service.ingest_diagnostic(
                    payload.model_dump()
                )
            )
        )

    return app


def _create_services(settings: MasterSettings, database: MasterDatabase) -> MasterServices:
    app_repo = AppRepo(database.connection)
    run_repo = RunRepo(database.connection)
    worker_repo = WorkerRepo(database.connection)
    image_repo = ImageRepo(database.connection)
    upload_repo = UploadRepo(database.connection)
    production_readiness_repo = ProductionReadinessRepo(database.connection)
    return MasterServices(
        app_service=AppService(app_repo),
        run_service=RunService(run_repo),
        worker_service=WorkerService(
            worker_repo,
            run_repo=run_repo,
            app_repo=app_repo,
            data_root=settings.data_root,
        ),
        upload_service=UploadService(run_repo, upload_repo),
        model_gateway_service=ModelGatewayProxyService(
            audit_root=settings.data_root
        ),
        production_readiness_service=ProductionReadinessService(
            production_readiness_repo
        ),
        image_repo=image_repo,
        redis_client=MemoryRedisClient(),
    )
