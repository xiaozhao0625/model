from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.model_gateway.contracts import (
    ActRequest,
    ActionProposal,
    ActionType,
    GroundRequest,
    GroundResult,
    ModelGatewayProvider,
    ModelTaskType,
    SceneClassifyRequest,
    SceneClassifyResult,
)
from ai_screenshot_platform.common.model_gateway.risk_rules import RiskRuleDetector
from ai_screenshot_platform.common.model_gateway.safety import ModelActionSafetyGate


class ModelGatewayServiceError(ValueError):
    pass


class ModelGatewayService:
    def __init__(
        self,
        provider: ModelGatewayProvider,
        audit_log_path: str | Path | None = None,
        run_dir: str | Path | None = None,
        risk_detector: RiskRuleDetector | None = None,
        safety_gate: ModelActionSafetyGate | None = None,
    ) -> None:
        self.provider = provider
        self.provider_name = provider.provider_name
        self.run_dir = Path(run_dir).resolve() if run_dir is not None else None
        self.audit_log_path = self._resolve_audit_log_path(
            audit_log_path=audit_log_path,
            run_dir=self.run_dir,
        )
        self.risk_detector = risk_detector or RiskRuleDetector()
        self.safety_gate = safety_gate or ModelActionSafetyGate()

    def scene_classify(
        self,
        request: SceneClassifyRequest,
    ) -> SceneClassifyResult:
        return self.provider.scene_classify(request)

    def ground(self, request: GroundRequest) -> GroundResult:
        return self.provider.ground(request)

    def act(self, request: ActRequest) -> ActionProposal:
        input_risk_flags = self.risk_detector.detect_act_request(request)
        if input_risk_flags:
            final_proposal = ActionProposal(
                action_type=ActionType.REQUEST_MANUAL,
                confidence=1.0,
                reason=(
                    "blocked forbidden input risk flags: "
                    + ", ".join(input_risk_flags)
                ),
                target=None,
                keys=[],
                risk_flags=input_risk_flags,
                provider_name=self.provider_name,
            )
            self._write_audit_log(
                request=request,
                input_risk_flags=input_risk_flags,
                output_risk_flags=input_risk_flags,
                final_proposal=final_proposal,
                blocked=True,
            )
            return final_proposal

        provider_proposal = self.provider.act(request)
        merged_risk_flags = self._merge_risk_flags(
            input_risk_flags,
            provider_proposal.risk_flags,
        )
        proposal_with_merged_risks = replace(
            provider_proposal,
            risk_flags=merged_risk_flags,
        )
        final_proposal = self.safety_gate.validate(proposal_with_merged_risks)
        blocked = final_proposal.action_type != provider_proposal.action_type
        self._write_audit_log(
            request=request,
            input_risk_flags=input_risk_flags,
            output_risk_flags=merged_risk_flags,
            final_proposal=final_proposal,
            blocked=blocked,
        )
        return final_proposal

    def _merge_risk_flags(
        self,
        input_risk_flags: list[str],
        output_risk_flags: list[str],
    ) -> list[str]:
        return sorted({*input_risk_flags, *output_risk_flags})

    def _resolve_audit_log_path(
        self,
        audit_log_path: str | Path | None,
        run_dir: Path | None,
    ) -> Path | None:
        if audit_log_path is None and run_dir is None:
            return None

        if run_dir is not None:
            resolved_run_dir = run_dir.resolve()
            resolved_path = (
                resolved_run_dir / "model_gateway.log"
                if audit_log_path is None
                else Path(audit_log_path).resolve()
            )
            if not resolved_path.is_relative_to(resolved_run_dir):
                raise ModelGatewayServiceError(
                    "audit_log_path must stay inside run_dir"
                )
            return resolved_path

        return Path(audit_log_path).resolve()

    def _write_audit_log(
        self,
        request: ActRequest,
        input_risk_flags: list[str],
        output_risk_flags: list[str],
        final_proposal: ActionProposal,
        blocked: bool,
    ) -> None:
        if self.audit_log_path is None:
            raise ModelGatewayServiceError(
                "act audit requires explicit audit_log_path or run_dir"
            )

        event: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "app_id": request.app_id,
            "run_id": request.run_id,
            "task_type": ModelTaskType.ACT.value,
            "provider_name": self.provider_name,
            "input_risk_flags": input_risk_flags,
            "output_risk_flags": output_risk_flags,
            "final_action_type": final_proposal.action_type.value,
            "blocked": blocked,
            "reason": final_proposal.reason,
        }
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log_path.open("a", encoding="utf-8", newline="\n") as log_file:
            log_file.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
            log_file.write("\n")
