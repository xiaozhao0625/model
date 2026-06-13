from __future__ import annotations

from pathlib import Path

from ai_screenshot_platform.common.model_gateway.contracts import (
    ActRequest,
    GroundRequest,
    SceneClass,
    SceneClassifyRequest,
)
from ai_screenshot_platform.common.model_gateway.gateway_service import (
    ModelGatewayService as CommonModelGatewayService,
)
from ai_screenshot_platform.common.model_gateway.mock_provider import (
    MockModelGatewayProvider,
)


class ModelGatewayProxyService:
    def __init__(self, audit_root: str | Path) -> None:
        self.audit_root = Path(audit_root)
        self.provider = MockModelGatewayProvider()

    def scene_classify(self, request: SceneClassifyRequest):
        return self._service_for_run(request.run_id).scene_classify(request)

    def ground(self, request: GroundRequest):
        return self._service_for_run(request.run_id).ground(request)

    def act(
        self,
        app_id: str,
        run_id: str,
        screenshot_path: str,
        scene_class: str,
        instruction: str,
        target_description: str | None,
        context: dict,
    ):
        request = ActRequest(
            app_id=app_id,
            run_id=run_id,
            screenshot_path=screenshot_path,
            scene_class=SceneClass(scene_class),
            instruction=instruction,
            target_description=target_description,
            context=context,
        )
        return self._service_for_run(run_id).act(request)

    def _service_for_run(self, run_id: str) -> CommonModelGatewayService:
        run_dir = self.audit_root / run_id
        return CommonModelGatewayService(provider=self.provider, run_dir=run_dir)
