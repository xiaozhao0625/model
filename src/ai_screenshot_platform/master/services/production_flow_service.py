from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_screenshot_platform.common.domain.run_status import RunStatus
from ai_screenshot_platform.master.repositories.run_repo import RunRepo
from ai_screenshot_platform.master.repositories.worker_repo import WorkerRepo
from ai_screenshot_platform.master.services.run_service import infer_worker_id_from_run_id


SMALL_SCALE_MAX_IMAGES = 50
SAFE_WORKER_ROOTS = {
    "M0": r"E:\work",
    "W1": r"D:\work",
    "W2": r"D:\work",
    "W3": r"D:\work",
}
PROTECTED_RUN_PREFIXES = ("p14_4_batch", "p14_3_", "p14_w")
TEST_CLEANUP_PREFIX = "p14_5_cleanup_test_"
MANUAL_STATUSES = {
    RunStatus.WAITING_MANUAL,
    RunStatus.NEEDS_MANUAL_SEED,
    RunStatus.MANUAL_REQUIRED,
    RunStatus.FAILED_LOW_YIELD,
    RunStatus.SKIPPED_RISK,
    RunStatus.BLOCKED,
    RunStatus.FAILED_TOOL_ERROR,
    RunStatus.FAILED_WORKER_LOST,
    RunStatus.FAILED_TIMEOUT,
}
FINAL_STATUSES = {
    RunStatus.UPLOADED_CONFIRMED,
    RunStatus.LOCAL_DELETE_PENDING,
    RunStatus.LOCAL_DELETED,
    RunStatus.COMPLETED,
    RunStatus.FAILED_LOW_YIELD,
    RunStatus.SKIPPED_RISK,
    RunStatus.CANCELLED,
}


class ProductionFlowService:
    def __init__(
        self,
        run_repo: RunRepo,
        worker_repo: WorkerRepo,
        data_root: str | Path = "runs/master",
    ) -> None:
        self.run_repo = run_repo
        self.worker_repo = worker_repo
        self.data_root = Path(data_root)

    def validate_batch_tasks(self, payload: dict[str, Any]) -> dict[str, Any]:
        tasks = self._payload_tasks(payload)
        results = [self._validate_task(index, task) for index, task in enumerate(tasks)]
        valid_count = sum(1 for item in results if item["valid"])
        return {
            "status": "valid" if valid_count == len(results) else "blocked",
            "dry_run": bool(payload.get("dry_run", True)),
            "production_scale_capture": False,
            "online_inference": False,
            "model_action_control": False,
            "task_count": len(results),
            "valid_count": valid_count,
            "blocked_count": len(results) - valid_count,
            "tasks": results,
        }

    def import_batch_tasks(self, payload: dict[str, Any]) -> dict[str, Any]:
        validation = self.validate_batch_tasks(payload)
        dry_run = bool(payload.get("dry_run", True))
        if dry_run or validation["blocked_count"]:
            return {
                **validation,
                "status": "dry_run_only" if dry_run else "blocked",
                "created_runs": [],
            }

        created: list[dict[str, Any]] = []
        for item in validation["tasks"]:
            run_id = str(item["run_id"])
            if self.run_repo.get(run_id) is not None:
                created.append({"run_id": run_id, "status": "already_exists"})
                continue
            record = self.run_repo.create(
                record=item["record"],
            )
            created.append({"run_id": record.run_id, "status": record.status.value})
        return {
            **validation,
            "status": "imported",
            "created_runs": created,
        }

    def claim_guard(self, worker_id: str, run_id: str) -> dict[str, Any]:
        run = self.run_repo.get(run_id)
        worker = self.worker_repo.get(worker_id)
        expected_worker = run.worker_id if run and run.worker_id else infer_worker_id_from_run_id(run_id)
        reasons: list[str] = []
        if run is None:
            reasons.append("run_not_found")
        if worker is None:
            reasons.append("worker_not_registered")
        if expected_worker and expected_worker != worker_id:
            reasons.append("worker_mismatch")
        if run is not None and run.status in FINAL_STATUSES:
            reasons.append("run_already_final_or_upload_state")
        allowed = not reasons
        return {
            "status": "allowed" if allowed else "blocked",
            "allowed": allowed,
            "run_id": run_id,
            "worker_id": worker_id,
            "expected_worker_id": expected_worker,
            "reasons": reasons,
            "no_worker_direct_postgresql": True,
            "no_model_action_control": True,
        }

    def manual_required_queue(self) -> dict[str, Any]:
        items = []
        for run in self.run_repo.list():
            reason = None
            if run.status in MANUAL_STATUSES:
                reason = run.status.value
            elif run.status == RunStatus.CAPTURE_COMPLETED and run.valid_total < max(1, min(run.target_min, SMALL_SCALE_MAX_IMAGES)):
                reason = "capture_completed_below_target_min"
            if reason:
                items.append(
                    {
                        "run_id": run.run_id,
                        "app_id": run.app_id,
                        "status": run.status.value,
                        "valid_total": run.valid_total,
                        "target_min": run.target_min,
                        "worker_id": run.worker_id or infer_worker_id_from_run_id(run.run_id),
                        "reason": reason,
                        "operator_action": "review_or_mark_final_status",
                    }
                )
        return {"status": "ok", "count": len(items), "items": items}

    def retry_plan(self, run_id: str) -> dict[str, Any]:
        run = self._get_run(run_id)
        blocked = run.status in {RunStatus.SKIPPED_RISK, RunStatus.CANCELLED, RunStatus.UPLOADED_CONFIRMED, RunStatus.LOCAL_DELETED, RunStatus.COMPLETED}
        retry_allowed = not blocked and run.retry_round < 2
        if run.status == RunStatus.FAILED_LOW_YIELD:
            action = "retry_with_lower_target_or_manual_required"
        elif run.status in {RunStatus.FAILED_TOOL_ERROR, RunStatus.FAILED_TIMEOUT, RunStatus.FAILED_WORKER_LOST}:
            action = "retry_same_worker_after_health_check"
        elif run.status == RunStatus.CAPTURE_COMPLETED and run.valid_total < run.target_min:
            action = "manual_required_low_yield_review"
        else:
            action = "no_retry_needed"
            retry_allowed = False
        return {
            "run_id": run_id,
            "status": run.status.value,
            "retry_allowed": retry_allowed,
            "retry_round": run.retry_round,
            "recommended_action": action,
            "online_inference": False,
            "model_action_control": False,
        }

    def upload_preview(self, run_id: str) -> dict[str, Any]:
        run = self._get_run(run_id)
        allowed = run.status in {RunStatus.CAPTURE_COMPLETED, RunStatus.UPLOAD_PENDING, RunStatus.UPLOADED_CONFIRMED}
        return {
            "run_id": run_id,
            "status": "ready" if allowed else "blocked",
            "run_status": run.status.value,
            "would_generate_upload_manifest": allowed and run.status == RunStatus.CAPTURE_COMPLETED,
            "would_mark_upload_pending": allowed and run.status == RunStatus.CAPTURE_COMPLETED,
            "automatic_upload": False,
            "requires_operator_confirmation": True,
            "blocked_reason": None if allowed else "run_not_capture_completed",
        }

    def cleanup_preview(self, run_id: str) -> dict[str, Any]:
        run = self._get_run(run_id)
        protected = run_id.startswith(PROTECTED_RUN_PREFIXES) and not run_id.startswith(TEST_CLEANUP_PREFIX)
        allowed_status = run.status == RunStatus.UPLOADED_CONFIRMED
        metadata = self._cleanup_metadata(run_id)
        blocked: list[str] = []
        if not allowed_status:
            blocked.append("requires_uploaded_confirmed")
        if protected:
            blocked.append("protected_p14_trial_run")
        if not metadata["has_upload_manifest"]:
            blocked.append("missing_upload_manifest")
        if not metadata["has_upload_record"]:
            blocked.append("missing_upload_record")
        return {
            "run_id": run_id,
            "status": "ready" if not blocked else "blocked",
            "run_status": run.status.value,
            "delete_allowed": not blocked,
            "preview_only": True,
            "blocked": blocked,
            **metadata,
        }

    def cleanup_execute(self, run_id: str, operator_confirm: bool = False) -> dict[str, Any]:
        preview = self.cleanup_preview(run_id)
        if preview["status"] != "ready" or not operator_confirm:
            return {
                **preview,
                "status": "blocked",
                "execute_result": "not_executed",
                "blocked": list(preview.get("blocked", [])) + ([] if operator_confirm else ["operator_confirmation_required"]),
            }
        run_dir = self._safe_local_run_dir(run_id)
        cleanup_marker = run_dir / "cleanup_record.json"
        cleanup_marker.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "status": RunStatus.LOCAL_DELETED.value,
                    "deleted_screenshots": False,
                    "operator_confirmed": True,
                    "changed_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.run_repo.update_status(run_id, RunStatus.LOCAL_DELETED)
        return {**preview, "status": "executed", "execute_result": "metadata_cleanup_record_written"}

    def disk_status(self) -> dict[str, Any]:
        nodes = []
        for role, root in SAFE_WORKER_ROOTS.items():
            path = Path(root)
            if role == "M0" and path.exists():
                usage = shutil.disk_usage(path)
                free_gb = round(usage.free / (1024 ** 3), 2)
                total_gb = round(usage.total / (1024 ** 3), 2)
                status = "ok" if free_gb >= 20 else "low_space"
                nodes.append({"role": role, "root": root, "status": status, "free_gb": free_gb, "total_gb": total_gb})
            else:
                nodes.append({"role": role, "root": root, "status": "remote_check_required", "free_gb": None, "total_gb": None})
        return {"status": "ok", "nodes": nodes, "production_scale_capture": False}

    def diagnostic_bundle(self, run_id: str, include_samples: bool = False) -> dict[str, Any]:
        run = self._get_run(run_id)
        bundle_dir = self.data_root / "diagnostic_bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        zip_path = bundle_dir / f"{run_id}_diagnostic_bundle.zip"
        payload = {
            "run": {
                "run_id": run.run_id,
                "app_id": run.app_id,
                "status": run.status.value,
                "valid_total": run.valid_total,
                "worker_id": run.worker_id or infer_worker_id_from_run_id(run.run_id),
            },
            "events": [
                {
                    "previous_status": event.previous_status.value,
                    "new_status": event.new_status.value,
                    "operator_action": event.operator_action,
                    "changed_at": event.changed_at,
                }
                for event in self.run_repo.status_events(run_id)
            ],
            "include_samples": include_samples,
            "screenshots_included": False,
            "secrets_included": False,
        }
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("diagnostic.json", json.dumps(payload, ensure_ascii=False, indent=2))
            archive.writestr("README.txt", "P14.5 diagnostic bundle: metadata only, no screenshots, no secrets.\n")
        return {
            "run_id": run_id,
            "status": "created",
            "bundle_path": str(zip_path),
            "include_samples": include_samples,
            "screenshots_included": False,
            "secrets_included": False,
        }

    def stuck_task_recovery(self, dry_run: bool = True) -> dict[str, Any]:
        workers = {worker.current_run_id: worker for worker in self.worker_repo.list() if worker.current_run_id}
        candidates = []
        for run in self.run_repo.list():
            if run.status not in {RunStatus.LAUNCHING, RunStatus.PROFILING, RunStatus.RUNNING, RunStatus.DISPATCHING}:
                continue
            worker = workers.get(run.run_id)
            candidates.append(
                {
                    "run_id": run.run_id,
                    "status": run.status.value,
                    "worker_id": run.worker_id or infer_worker_id_from_run_id(run.run_id),
                    "worker_has_current_run": worker is not None,
                    "recommended_action": "no_action" if worker else "mark_failed_worker_lost_or_requeue",
                }
            )
        return {
            "status": "dry_run" if dry_run else "blocked",
            "dry_run": dry_run,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "mutated": False,
        }

    def operator_dashboard(self) -> dict[str, Any]:
        records = self.run_repo.list()
        status_counts: dict[str, int] = {}
        for run in records:
            status_counts[run.status.value] = status_counts.get(run.status.value, 0) + 1
        return {
            "status": "ok",
            "run_count": len(records),
            "status_counts": status_counts,
            "manual_required": self.manual_required_queue()["count"],
            "disk": self.disk_status(),
            "guards": {
                "production_scale_capture": False,
                "online_inference": False,
                "model_action_control": False,
                "automatic_upload": False,
                "unconfirmed_cleanup": False,
            },
        }

    def _payload_tasks(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        tasks = payload.get("tasks", payload)
        if not isinstance(tasks, list):
            raise ValueError("batch task payload must include tasks[]")
        return [task for task in tasks if isinstance(task, dict)]

    def _validate_task(self, index: int, task: dict[str, Any]) -> dict[str, Any]:
        from ai_screenshot_platform.master.models.entities import RunRecord

        run_id = str(task.get("run_id") or f"p14_5_task_{index:03d}")
        app_id = str(task.get("app_id") or "")
        role = str(task.get("role") or task.get("worker_role") or "")
        capture_method = str(task.get("capture_method") or "")
        target_total = int(task.get("target_total") or task.get("target_max") or 0)
        blocked: list[str] = []
        if not app_id:
            blocked.append("missing_app_id")
        if role not in {"W1", "W2", "W3"}:
            blocked.append("unsupported_role")
        if target_total < 1 or target_total > SMALL_SCALE_MAX_IMAGES:
            blocked.append("target_total_outside_small_scale_limit")
        if "testsrc" in capture_method:
            blocked.append("test_source_not_allowed_for_production_flow")
        lowered = " ".join(str(value).lower() for value in task.values())
        for token in ("login", "captcha", "payment", "apk", "game", "手游", "验证码", "支付", "登录"):
            if token in lowered and "pc_game_capture_priority" not in lowered:
                blocked.append(f"blocked_sensitive_target:{token}")
                break
        worker_id = task.get("worker_id") or infer_worker_id_from_run_id(run_id)
        record = RunRecord(
            run_id=run_id,
            app_id=app_id,
            status=RunStatus.PENDING,
            target_min=target_total,
            target_max=target_total,
            worker_id=str(worker_id) if worker_id else None,
        )
        return {
            "index": index,
            "run_id": run_id,
            "app_id": app_id,
            "role": role,
            "capture_method": capture_method,
            "target_total": target_total,
            "worker_id": worker_id,
            "valid": not blocked,
            "blocked": blocked,
            "record": record,
        }

    def _get_run(self, run_id: str):
        run = self.run_repo.get(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def _safe_local_run_dir(self, run_id: str) -> Path:
        if not run_id.startswith(TEST_CLEANUP_PREFIX):
            raise ValueError("cleanup execute is only enabled for p14.5 test cleanup runs")
        run_dir = (self.data_root / run_id).resolve()
        root = self.data_root.resolve()
        if root not in run_dir.parents and run_dir != root:
            raise ValueError("cleanup path escapes data root")
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _cleanup_metadata(self, run_id: str) -> dict[str, Any]:
        run_dir = (self.data_root / run_id).resolve()
        return {
            "run_dir": str(run_dir),
            "has_upload_manifest": (run_dir / "upload_manifest.json").is_file(),
            "has_upload_record": (run_dir / "upload_record.json").is_file(),
            "has_summary_json": (run_dir / "summary.json").is_file(),
            "has_meta_jsonl": (run_dir / "meta.jsonl").is_file(),
            "screenshot_delete_preview_count": 0,
            "metadata_delete_preview_count": 0,
        }
