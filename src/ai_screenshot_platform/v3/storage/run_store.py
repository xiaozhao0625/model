from __future__ import annotations

import json
import os
import shutil
import uuid
import zipfile
from pathlib import Path

from ai_screenshot_platform.v3.schemas import (
    V3CollectionExportResult,
    V3CollectionRecord,
    V3CollectionSummary,
    V3Event,
    V3ImageRecord,
    V3RunRecord,
    V3Summary,
    V3TaskConfig,
    ensure_run_dir,
    utc_now,
)


class V3RunStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else _default_v3_runs_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def create_collection(self, config: V3TaskConfig) -> V3CollectionRecord:
        config = config.model_copy(deep=True)
        collection_id = config.collection_id or self._collection_id_for(config)
        try:
            return self.get_collection(collection_id)
        except KeyError:
            pass
        config.collection_id = collection_id
        display_name = config.display_name or config.task_name or config.app_name or collection_id
        config.display_name = display_name
        self._ensure_collection_io_dirs(config, collection_id, display_name)
        record = V3CollectionRecord(
            collection_id=collection_id,
            config=config,
            task_name=config.task_name,
            app_name=config.app_name,
            display_name=display_name,
        )
        self._write_collection(record)
        self._write_collection_json(collection_id, "collection_index.json", {"accepted_unique": []})
        return record

    def list_collections(self) -> list[V3CollectionRecord]:
        records: list[V3CollectionRecord] = []
        for path in sorted(self._collections_root().glob("*/collection.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            record = self._read_collection_file(path)
            if record is None:
                continue
            if record.status != "deleted":
                records.append(record)
        return records

    def list_deleted_collections(self) -> list[V3CollectionRecord]:
        records: list[V3CollectionRecord] = []
        for path in sorted(self._collections_root().glob("*/collection.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            record = self._read_collection_file(path)
            if record is None:
                continue
            if record.status == "deleted":
                records.append(record)
        return records

    def get_collection(self, collection_id: str) -> V3CollectionRecord:
        path = self._collection_dir(collection_id) / "collection.json"
        if not path.is_file():
            raise KeyError(f"v3 collection not found: {collection_id}")
        record = self._read_collection_file(path)
        if record is None:
            raise KeyError(f"v3 collection metadata is corrupted: {collection_id}")
        return record

    def create_run(self, config: V3TaskConfig, collection_id: str | None = None) -> V3RunRecord:
        config = config.model_copy(deep=True)
        if collection_id is not None:
            config.collection_id = collection_id
        collection = self.create_collection(config)
        run_id = f"v3_{utc_now().replace(':', '').replace('+', '_').replace('.', '_')}_{uuid.uuid4().hex[:8]}"
        display_name = config.display_name or config.task_name or config.app_name or run_id
        config.display_name = display_name
        config.collection_id = collection.collection_id
        self._ensure_collection_io_dirs(config, collection.collection_id, display_name)
        round_index = len(collection.run_ids) + 1
        record = V3RunRecord(
            run_id=run_id,
            collection_id=collection.collection_id,
            round_index=round_index,
            config=config,
            task_name=config.task_name,
            app_name=config.app_name,
            display_name=display_name,
        )
        self._write_run(record)
        collection.run_ids.append(run_id)
        collection.latest_run_id = run_id
        collection.updated_at = utc_now()
        self._write_collection(collection)
        self.append_event(run_id, "run_created", {"observe_only": config.observe_only})
        return record

    def list_runs(self) -> list[V3RunRecord]:
        records: list[V3RunRecord] = []
        for path in sorted(self.root.glob("*/run.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            record = self._read_run_file(path)
            if record is None:
                continue
            if record.status != "deleted":
                records.append(record)
        return records

    def get_run(self, run_id: str) -> V3RunRecord:
        path = self._run_path(run_id)
        if not path.is_file():
            raise KeyError(f"v3 run not found: {run_id}")
        record = self._read_run_file(path)
        if record is None:
            raise KeyError(f"v3 run metadata is corrupted: {run_id}")
        return record

    def update_status(self, run_id: str, status: str, error: str | None = None) -> V3RunRecord:
        record = self.get_run(run_id)
        record.status = status  # type: ignore[assignment]
        record.updated_at = utc_now()
        record.last_error = error
        self._write_run(record)
        self.append_event(run_id, "status_changed", {"status": status, "error": error})
        return record

    def add_image(self, run_id: str, image: V3ImageRecord) -> V3ImageRecord:
        record = self.get_run(run_id)
        if image.bucket == "accepted" and record.collection_id:
            image = self._apply_collection_unique_index(record, image)
        image_path = self._run_dir(run_id) / "images.jsonl"
        with image_path.open("a", encoding="utf-8") as file:
            file.write(image.model_dump_json() + "\n")
        self._recount(run_id)
        self.append_event(run_id, "image_added", {"image_id": image.image_id, "bucket": image.bucket})
        if record.collection_id:
            self.refresh_collection_summary(record.collection_id)
        return image

    def collection_images(self, collection_id: str, unique_only: bool = False) -> list[V3ImageRecord]:
        collection = self.get_collection(collection_id)
        images: list[V3ImageRecord] = []
        for run_id in collection.run_ids:
            for image in self.list_images(run_id):
                if unique_only and not bool(image.meta.get("collection_unique")):
                    continue
                images.append(image)
        return images

    def continue_collection(self, collection_id: str) -> V3RunRecord:
        collection = self.get_collection(collection_id)
        config = collection.config.model_copy(deep=True)
        config.collection_id = collection_id
        return self.create_run(config, collection_id=collection_id)

    def stop_collection(self, collection_id: str) -> V3CollectionRecord:
        collection = self.get_collection(collection_id)
        collection.status = "stopped"
        collection.updated_at = utc_now()
        self._write_collection(collection)
        for run_id in collection.run_ids:
            try:
                run = self.get_run(run_id)
            except KeyError:
                continue
            if run.status not in {"completed", "stopped", "failed"}:
                self.update_status(run_id, "stopped")
        return collection

    def delete_collection(self, collection_id: str, delete_files: bool = False) -> dict[str, object]:
        collection = self.get_collection(collection_id)
        active = {"running", "waiting_for_input", "waiting_for_input_timeout"}
        for run_id in collection.run_ids:
            try:
                if self.get_run(run_id).status in active:
                    raise ValueError("collection_has_running_run")
            except KeyError:
                continue
        if delete_files:
            moved_to = self._move_collection_to_trash(collection)
            return {
                "target_type": "collection",
                "target_id": collection_id,
                "status": "deleted_to_trash",
                "delete_files": True,
                "moved_to": str(moved_to),
                "message": "采集项目文件已移动到回收站。",
            }
        collection.status = "deleted"
        collection.updated_at = utc_now()
        self._write_collection(collection)
        self._write_delete_audit("collection", collection_id, False, None)
        return {
            "target_type": "collection",
            "target_id": collection_id,
            "status": "deleted",
            "delete_files": False,
            "moved_to": None,
            "message": "采集项目已软删除，可在已删除任务中恢复。",
        }

    def restore_collection(self, collection_id: str) -> V3CollectionRecord:
        collection = self.get_collection(collection_id)
        if collection.status != "deleted":
            return collection
        collection.status = "stopped"
        collection.updated_at = utc_now()
        self._write_collection(collection)
        return collection

    def delete_run(self, run_id: str, delete_files: bool = False) -> dict[str, object]:
        run = self.get_run(run_id)
        if run.status in {"running", "waiting_for_input", "waiting_for_input_timeout"}:
            raise ValueError("run_is_running")
        if delete_files:
            moved_to = self._move_run_to_trash(run)
            if run.collection_id:
                self.refresh_collection_summary(run.collection_id)
            return {
                "target_type": "run",
                "target_id": run_id,
                "status": "deleted_to_trash",
                "delete_files": True,
                "moved_to": str(moved_to),
                "message": "轮次文件已移动到回收站。",
            }
        run.status = "deleted"
        run.updated_at = utc_now()
        self._write_run(run)
        self._write_delete_audit("run", run_id, False, None, collection_id=run.collection_id)
        if run.collection_id:
            self.refresh_collection_summary(run.collection_id)
        return {
            "target_type": "run",
            "target_id": run_id,
            "status": "deleted",
            "delete_files": False,
            "moved_to": None,
            "message": "轮次已软删除，collection 汇总已重算。",
        }

    def refresh_collection_summary(self, collection_id: str) -> V3CollectionSummary:
        summary = self.collection_summary(collection_id)
        collection = self.get_collection(collection_id)
        if collection.status != summary.status:
            collection.status = summary.status  # type: ignore[assignment]
            collection.updated_at = utc_now()
            self._write_collection(collection)
        self._write_collection_json(collection_id, "collection_summary.json", summary.model_dump())
        return summary

    def collection_summary(self, collection_id: str) -> V3CollectionSummary:
        collection = self.get_collection(collection_id)
        if self._ensure_collection_io_dirs(
            collection.config,
            collection.collection_id,
            collection.display_name or collection.task_name or collection.app_name or collection.collection_id,
        ):
            self._write_collection(collection)
        run_summaries: list[dict[str, object]] = []
        processed_total = accepted_total = rejected_total = failed_total = action_total = 0
        duplicate_across_runs_total = accepted_unique_total = visual_fill_total = 0
        latest_round: dict[str, object] | None = None
        latest_action: dict[str, object] | None = None
        for index, run_id in enumerate(collection.run_ids, start=1):
            try:
                run_record = self.get_run(run_id)
            except KeyError:
                continue
            if run_record.status == "deleted":
                continue
            images = self.list_images(run_id)
            actions = self.list_meta_jsonl(run_id, "actions.jsonl")
            if actions:
                latest_action = actions[-1]
            accepted = [image for image in images if image.bucket == "accepted"]
            rejected = [image for image in images if image.bucket == "rejected"]
            new_unique = [image for image in accepted if bool(image.meta.get("collection_unique"))]
            cross_duplicates = [
                image
                for image in images
                if image.reject_reason == "rejected_duplicate_across_runs" or bool(image.meta.get("duplicate_across_runs"))
            ]
            run_failed = _folder_watch_metric(self._run_dir(run_id), "failed", 0)
            top_rejects = _top_reject_reasons(images)
            row = {
                "run_id": run_id,
                "status": run_record.status,
                "round_index": index,
                "processed": len(images),
                "accepted": len(accepted),
                "new_unique": len(new_unique),
                "duplicate_across_runs": len(cross_duplicates),
                "rejected": len(rejected),
                "failed": run_failed,
                "actions": len(actions),
                "top_reject_reasons": top_rejects,
            }
            run_summaries.append(row)
            latest_round = row
            processed_total += len(images)
            accepted_total += len(accepted) + len(cross_duplicates)
            rejected_total += len(rejected)
            failed_total += run_failed
            action_total += len(actions)
            accepted_unique_total += len(new_unique)
            duplicate_across_runs_total += len(cross_duplicates)
            visual_fill_total += sum(1 for image in new_unique if image.meta.get("accepted_class") == "accepted_visual_fill")
        config = collection.config
        status = _collection_status(
            collection,
            accepted_unique_total,
            any(row.get("status") in {"running", "waiting_for_input", "waiting_for_input_timeout"} for row in run_summaries),
        )
        suggestion = _continue_suggestion(latest_round, accepted_unique_total, config)
        summary = V3CollectionSummary(
            collection_id=collection_id,
            status=status,
            task_name=collection.task_name or config.task_name,
            app_name=collection.app_name or config.app_name,
            display_name=collection.display_name or config.display_name or config.task_name or config.app_name,
            app_type=config.app_type,
            target_language=config.target_language,
            text_policy=config.text_policy,
            input_dir=config.input_dir,
            frame_pump_output_dir=config.frame_pump_output_dir,
            watch_dir=config.watch_dir,
            target_accepted_min=config.target_accepted_min,
            target_accepted_soft=config.target_accepted_soft,
            target_accepted_max=config.target_accepted_max,
            processed_total=processed_total,
            accepted_total=accepted_total,
            accepted_unique_total=accepted_unique_total,
            duplicate_across_runs_total=duplicate_across_runs_total,
            rejected_total=rejected_total,
            failed_total=failed_total,
            action_total=action_total,
            run_count=len(run_summaries),
            latest_run_id=collection.latest_run_id,
            latest_round_index=int(latest_round.get("round_index", 0)) if latest_round else 0,
            latest_round_processed=int(latest_round.get("processed", 0)) if latest_round else 0,
            latest_round_accepted=int(latest_round.get("accepted", 0)) if latest_round else 0,
            latest_round_new_unique=int(latest_round.get("new_unique", 0)) if latest_round else 0,
            latest_round_duplicate_across_runs=int(latest_round.get("duplicate_across_runs", 0)) if latest_round else 0,
            latest_round_rejected=int(latest_round.get("rejected", 0)) if latest_round else 0,
            latest_round_failed=int(latest_round.get("failed", 0)) if latest_round else 0,
            latest_round_action_count=int(latest_round.get("actions", 0)) if latest_round else 0,
            latest_round_top_reject_reasons=list(latest_round.get("top_reject_reasons", [])) if latest_round else [],
            latest_action=latest_action,
            latest_blocked_reason=_action_blocked_reason(latest_action),
            game_agent_status=_game_agent_status(config, latest_action),
            game_agent_state=str((latest_action or {}).get("observed_state") or "unknown"),
            game_agent_enabled_capabilities=_game_agent_capabilities(config),
            min_target_reached=accepted_unique_total >= config.target_accepted_min,
            soft_target_reached=accepted_unique_total >= config.target_accepted_soft,
            max_target_reached=accepted_unique_total >= config.target_accepted_max,
            remaining_to_min=max(0, config.target_accepted_min - accepted_unique_total),
            remaining_to_soft=max(0, config.target_accepted_soft - accepted_unique_total),
            visual_fill_total=visual_fill_total,
            visual_fill_ratio=round(visual_fill_total / accepted_unique_total, 4) if accepted_unique_total else 0.0,
            continue_suggestion=suggestion,
            accepted_unique_dir=str((self._collection_dir(collection_id) / "accepted_unique").resolve()),
            export_dir=str((self._collection_dir(collection_id) / "exports").resolve()),
            runs=run_summaries,
        )
        return summary

    def export_collection(self, collection_id: str) -> V3CollectionExportResult:
        summary = self.refresh_collection_summary(collection_id)
        unique_images = self.collection_images(collection_id, unique_only=True)
        if not unique_images:
            raise ValueError("no_accepted_unique_images")
        export_dir = self._collection_dir(collection_id) / "exports" / utc_now().replace(":", "").replace("+", "_").replace(".", "_")
        images_dir = export_dir / "accepted_unique"
        images_dir.mkdir(parents=True, exist_ok=True)
        manifest: list[dict[str, object]] = []
        for image in unique_images:
            source = Path(image.path)
            dest = images_dir / source.name
            if source.is_file() and not dest.exists():
                shutil.copy2(source, dest)
            manifest.append(
                {
                    "image_id": image.image_id,
                    "source_path": image.path,
                    "export_path": str(dest),
                    "source_run_id": image.meta.get("collection_run_id"),
                    "accepted_reason": image.duplicate_decision.get("duplicate_decision_reason"),
                    "ocr_language": image.meta.get("ocr", {}).get("target_language") if isinstance(image.meta.get("ocr"), dict) else None,
                    "accepted_class": image.meta.get("accepted_class"),
                    "sha256": image.sha256,
                    "content_hash": image.content_hash,
                    "near_duplicate_signature": image.duplicate_decision.get("content_hash"),
                }
            )
        rejection_summary = _collection_rejection_summary(self.collection_images(collection_id))
        duplicate_summary = {
            "duplicate_across_runs_total": summary.duplicate_across_runs_total,
            "accepted_unique_total": summary.accepted_unique_total,
        }
        manifest_path = export_dir / "manifest.json"
        summary_path = export_dir / "summary.json"
        rejection_path = export_dir / "rejection_summary.json"
        duplicate_path = export_dir / "duplicate_summary.json"
        _write_json(manifest_path, manifest)
        _write_json(summary_path, summary.model_dump())
        _write_json(rejection_path, rejection_summary)
        _write_json(duplicate_path, duplicate_summary)
        archive_path = export_dir.with_suffix(".zip")
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in export_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(export_dir))
        return V3CollectionExportResult(
            collection_id=collection_id,
            status="exported",
            export_dir=str(export_dir),
            archive_path=str(archive_path),
            zip_path=str(archive_path),
            manifest_path=str(manifest_path),
            summary_path=str(summary_path),
            rejection_summary_path=str(rejection_path),
            duplicate_summary_path=str(duplicate_path),
            accepted_unique_total=summary.accepted_unique_total,
            message="导出成功",
        )

    def list_images(self, run_id: str) -> list[V3ImageRecord]:
        path = self._run_dir(run_id) / "images.jsonl"
        if not path.is_file():
            return []
        records: list[V3ImageRecord] = []
        for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(V3ImageRecord.model_validate_json(line))
            except Exception as exc:
                self._write_corrupt_metadata_audit(path, exc, line=index)
        return records

    def append_event(self, run_id: str, event: str, details: dict[str, object] | None = None) -> V3Event:
        entry = V3Event(event=event, details=details or {})
        path = self._run_dir(run_id) / "events.jsonl"
        with path.open("a", encoding="utf-8") as file:
            file.write(entry.model_dump_json() + "\n")
        self._increment(run_id, "events")
        return entry

    def list_events(self, run_id: str) -> list[V3Event]:
        path = self._run_dir(run_id) / "events.jsonl"
        if not path.is_file():
            return []
        records: list[V3Event] = []
        for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(V3Event.model_validate_json(line))
            except Exception as exc:
                self._write_corrupt_metadata_audit(path, exc, line=index)
        return records

    def run_dir(self, run_id: str) -> Path:
        self.get_run(run_id)
        return self._run_dir(run_id)

    def write_artifact(self, run_id: str, name: str, payload: object) -> Path:
        path = self._run_dir(run_id) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def append_meta_jsonl(self, run_id: str, name: str, payload: object) -> Path:
        path = self._run_dir(run_id) / "meta" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")
        if name == "actions.jsonl":
            self._increment(run_id, "actions")
        return path

    def list_meta_jsonl(self, run_id: str, name: str) -> list[dict[str, object]]:
        path = self._run_dir(run_id) / "meta" / name
        if not path.is_file():
            return []
        records: list[dict[str, object]] = []
        for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(item)
            except Exception as exc:
                self._write_corrupt_metadata_audit(path, exc, line=index)
        return records

    def summary(
        self,
        run_id: str,
        ocr_ready: bool,
        model_ready: bool,
        safety_gate_ready: bool,
        ocr_gpu_ready: bool = False,
        ocr_performance_ready: bool = False,
        ocr_production_ready: bool | None = None,
        input_gateway_ready: bool = False,
        cursor_read_ready: bool = False,
        mouse_click_ready: bool = False,
        same_desktop_session_ready: bool = False,
        same_integrity_ready: bool = False,
        interactive_desktop_ready: bool = False,
        click_backend: str = "dry_run_backend",
        input_gateway_blockers: list[str] | None = None,
        readiness_blockers: list[str] | None = None,
    ) -> V3Summary:
        record = self.get_run(run_id)
        events = self.list_events(run_id)
        images = self.list_images(run_id)
        actions = self.list_meta_jsonl(run_id, "actions.jsonl")
        accepted_images = [image for image in images if image.bucket == "accepted"]
        accepted_by_capture_reason = _count_meta_values(accepted_images, "capture_reason", "periodic")
        accepted_by_ui_state_hint = _count_meta_values(accepted_images, "ui_state_hint", "unknown")
        duplicate_summary = _duplicate_summary(images)
        failed = _folder_watch_metric(self._run_dir(run_id), "failed", 0)
        quarantined = _folder_watch_metric(self._run_dir(run_id), "quarantined", 0)
        action_state_count = _folder_watch_metric(self._run_dir(run_id), "action_state_count", 0)
        frame_pump_restart_count = _folder_watch_metric(self._run_dir(run_id), "frame_pump_restart_count", 0)
        frame_pump_heartbeat = _folder_watch_object(self._run_dir(run_id), "frame_pump_heartbeat")
        action_status_counts = _count_action_statuses(actions)
        region_counts = _count_action_regions(actions)
        auto_ready = (
            ocr_ready
            and model_ready
            and safety_gate_ready
            and not record.config.observe_only
            and record.config.enable_auto_click
        )
        production_ready = ocr_production_ready if ocr_production_ready is not None else ocr_gpu_ready and ocr_performance_ready
        full_auto_ready = auto_ready and production_ready
        summary = V3Summary(
            run_id=run_id,
            status=record.status,
            counts=record.counts,
            task_name=record.task_name or record.config.task_name,
            app_name=record.app_name or record.config.app_name,
            display_name=record.display_name or record.config.display_name or record.config.task_name or record.config.app_name,
            target_accepted_min=record.config.target_accepted_min,
            target_accepted_soft=record.config.target_accepted_soft,
            target_accepted_max=record.config.target_accepted_max,
            processed=len(images),
            accepted=sum(1 for image in images if image.bucket == "accepted"),
            rejected=sum(1 for image in images if image.bucket == "rejected"),
            failed=failed,
            quarantined=quarantined,
            manual_review_count=sum(1 for image in images if image.bucket == "manual_review"),
            action_state_count=action_state_count,
            near_duplicate_count=sum(1 for image in images if image.reject_reason == "near_duplicate"),
            exact_duplicate_count=duplicate_summary["exact_duplicate_count"],
            action_representative_accepted_count=duplicate_summary["action_representative_accepted_count"],
            visual_difference_accepted_count=duplicate_summary["visual_difference_accepted_count"],
            menu_state_accepted_count=duplicate_summary["menu_state_accepted_count"],
            dialog_state_accepted_count=duplicate_summary["dialog_state_accepted_count"],
            periodic_static_rejected_count=duplicate_summary["periodic_static_rejected_count"],
            duplicate_policy_summary=duplicate_summary["duplicate_policy_summary"],
            duplicate_explanation_report_path=str(self.root.parent.parent / "reports" / f"duplicate_explain_{run_id}.md"),
            frame_pump_restart_count=frame_pump_restart_count,
            frame_pump_heartbeat=frame_pump_heartbeat,
            content_area_blocked_count=region_counts["content_area_blocked"],
            ui_chrome_click_count=region_counts["ui_chrome_click"],
            unsafe_chrome_blocked_count=region_counts["unsafe_chrome_blocked"],
            reject_reason_distribution=_count_reject_reasons(images),
            accepted_by_capture_reason=accepted_by_capture_reason,
            accepted_by_ui_state_hint=accepted_by_ui_state_hint,
            accepted_text_ui_count=_accepted_class_count(accepted_images, "accepted_text_ui"),
            accepted_text_hud_count=_accepted_class_count(accepted_images, "accepted_text_hud"),
            accepted_visual_fill_count=_accepted_class_count(accepted_images, "accepted_visual_fill"),
            no_text_fill_ratio_actual=_visual_fill_ratio(accepted_images),
            no_text_fill_over_quota=_visual_fill_ratio(accepted_images) > record.config.no_text_fill_ratio,
            latest_input_at=images[-1].created_at if images else None,
            latest_accepted_at=accepted_images[-1].created_at if accepted_images else None,
            top_reject_reason=_top_reject_reason(images),
            auto_click_count=sum(1 for action in actions if _action_executed(action)),
            menu_opened_count=action_status_counts.get("menu_opened", 0),
            dialog_opened_count=action_status_counts.get("dialog_opened", 0),
            navigation_success_count=action_status_counts.get("navigation_success", 0),
            no_effect_count=action_status_counts.get("no_effect", 0),
            blocked_count=action_status_counts.get("blocked", 0) + action_status_counts.get("stopped", 0),
            rollback_count=action_status_counts.get("rollback_requested", 0) + action_status_counts.get("rollback", 0),
            risk_hit_count=action_status_counts.get("risk_hit", 0),
            observe_only=record.config.observe_only,
            auto_click_ready=auto_ready,
            full_auto_capture_ready=full_auto_ready,
            model_ready=model_ready,
            ocr_ready=ocr_ready,
            ocr_gpu_ready=ocr_gpu_ready,
            ocr_performance_ready=ocr_performance_ready,
            ocr_production_ready=production_ready,
            input_gateway_ready=input_gateway_ready,
            cursor_read_ready=cursor_read_ready,
            mouse_click_ready=mouse_click_ready,
            same_desktop_session_ready=same_desktop_session_ready,
            same_integrity_ready=same_integrity_ready,
            interactive_desktop_ready=interactive_desktop_ready,
            click_backend=click_backend,
            input_gateway_blockers=input_gateway_blockers or [],
            readiness_blockers=readiness_blockers or [],
            safety_gate_ready=safety_gate_ready,
            latest_event=events[-1] if events else None,
        )
        self.write_artifact(run_id, "summary.json", summary.model_dump())
        return summary

    def _run_dir(self, run_id: str) -> Path:
        return ensure_run_dir(str(self.root), run_id)

    def _run_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "run.json"

    def _collections_root(self) -> Path:
        root = self.root / "collections"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _collection_dir(self, collection_id: str) -> Path:
        path = self._collections_root() / collection_id
        path.mkdir(parents=True, exist_ok=True)
        for name in ("accepted_unique", "reports", "runs", "exports"):
            (path / name).mkdir(parents=True, exist_ok=True)
        return path

    def _ensure_collection_io_dirs(self, config: V3TaskConfig, collection_id: str, display_name: str) -> bool:
        previous = (config.input_dir, config.frame_pump_output_dir, config.watch_dir)
        configured = config.input_dir or config.frame_pump_output_dir or config.watch_dir
        if configured:
            input_dir = Path(configured)
        else:
            short_id = _collection_short_id(collection_id)
            safe_name = _safe_windows_name(display_name or collection_id)
            input_dir = _default_obs_output_root() / f"{safe_name}_{short_id}"
        input_dir.mkdir(parents=True, exist_ok=True)
        resolved = str(input_dir)
        config.input_dir = resolved
        config.frame_pump_output_dir = resolved
        config.watch_dir = resolved
        if config.enable_game_explorer and not config.enable_game_agent:
            config.enable_game_agent = True
        if config.enable_game_agent and config.game_agent_mode == "off":
            config.game_agent_mode = "auto_explore"
        if config.allow_wasd_mouse:
            config.allow_wasd = True
            config.allow_mouse_look = True
        if config.safe_game_scene_confirmed and not config.safe_scene_confirmed:
            config.safe_scene_confirmed = True
        return previous != (config.input_dir, config.frame_pump_output_dir, config.watch_dir)

    def _collection_id_for(self, config: V3TaskConfig) -> str:
        base = "|".join(
            [
                config.app_name,
                config.app_type,
                config.target_language,
                config.text_policy,
                config.capture_source,
                str(Path(config.save_root).resolve()),
                config.task_name or "",
            ]
        )
        safe_name = _slug(config.task_name or config.app_name or "collection")
        digest = uuid.uuid5(uuid.NAMESPACE_URL, base).hex[:10]
        return f"col_{safe_name}_{digest}"

    def _write_collection(self, record: V3CollectionRecord) -> None:
        path = self._collection_dir(record.collection_id) / "collection.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def _write_collection_json(self, collection_id: str, name: str, payload: object) -> Path:
        path = self._collection_dir(collection_id) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(path, payload)
        return path

    def _read_collection_index(self, collection_id: str) -> dict[str, object]:
        path = self._collection_dir(collection_id) / "collection_index.json"
        if not path.is_file():
            return {"accepted_unique": []}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"accepted_unique": []}
        return payload if isinstance(payload, dict) else {"accepted_unique": []}

    def _apply_collection_unique_index(self, run: V3RunRecord, image: V3ImageRecord) -> V3ImageRecord:
        collection_id = run.collection_id
        if not collection_id:
            return image
        index = self._read_collection_index(collection_id)
        accepted_unique = index.setdefault("accepted_unique", [])
        if not isinstance(accepted_unique, list):
            accepted_unique = []
            index["accepted_unique"] = accepted_unique
        signature = _image_signature(image)
        duplicate = _find_collection_duplicate(accepted_unique, signature, current_run_id=run.run_id)
        image.meta["collection_id"] = collection_id
        image.meta["collection_run_id"] = run.run_id
        image.meta["collection_round_index"] = run.round_index
        if duplicate:
            image.bucket = "rejected"
            image.reject_reason = "rejected_duplicate_across_runs"
            image.meta["collection_unique"] = False
            image.meta["duplicate_across_runs"] = True
            image.meta["duplicate_with_run_id"] = duplicate.get("run_id")
            image.meta["duplicate_with_image_id"] = duplicate.get("image_id")
            image.duplicate_decision["duplicate_across_runs"] = True
            image.duplicate_decision["compared_with_run_id"] = duplicate.get("run_id")
            image.duplicate_decision["compared_with_image_id"] = duplicate.get("image_id")
            image.duplicate_decision["duplicate_decision_reason"] = "rejected_duplicate_across_runs"
            return image
        image.meta["collection_unique"] = True
        row = {
            "run_id": run.run_id,
            "round_index": run.round_index,
            "image_id": image.image_id,
            "path": image.path,
            "sha256": image.sha256,
            "content_hash": image.content_hash,
            "ocr_text_signature": signature.get("ocr_text_signature"),
            "near_duplicate_signature": signature.get("near_duplicate_signature"),
            "accepted_class": image.meta.get("accepted_class"),
            "created_at": image.created_at,
        }
        accepted_unique.append(row)
        self._write_collection_json(collection_id, "collection_index.json", index)
        source = Path(image.path)
        if source.is_file():
            dest = self._collection_dir(collection_id) / "accepted_unique" / f"{run.round_index:03d}_{image.image_id}{source.suffix}"
            if not dest.exists():
                shutil.copy2(source, dest)
            image.meta["collection_unique_path"] = str(dest)
        return image

    def _write_run(self, record: V3RunRecord) -> None:
        path = self._run_path(record.run_id)
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def _read_collection_file(self, path: Path) -> V3CollectionRecord | None:
        try:
            return V3CollectionRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            self._write_corrupt_metadata_audit(path, exc)
            return None

    def _read_run_file(self, path: Path) -> V3RunRecord | None:
        try:
            return V3RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            self._write_corrupt_metadata_audit(path, exc)
            return None

    def _trash_root(self) -> Path:
        path = self.root / "trash"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _move_collection_to_trash(self, collection: V3CollectionRecord) -> Path:
        stamp = utc_now().replace(":", "").replace("+", "_").replace(".", "_")
        target = self._trash_root() / f"{stamp}_{collection.collection_id}"
        target.mkdir(parents=True, exist_ok=True)
        collection_dir = self._collection_dir(collection.collection_id)
        if collection_dir.exists():
            shutil.move(str(collection_dir), str(target / "collection"))
        for run_id in collection.run_ids:
            run_dir = self.root / run_id
            if run_dir.exists():
                shutil.move(str(run_dir), str(target / f"run_{run_id}"))
        self._write_delete_audit("collection", collection.collection_id, True, target)
        return target

    def _move_run_to_trash(self, run: V3RunRecord) -> Path:
        stamp = utc_now().replace(":", "").replace("+", "_").replace(".", "_")
        target = self._trash_root() / f"{stamp}_{run.run_id}"
        run_dir = self.root / run.run_id
        if run_dir.exists():
            shutil.move(str(run_dir), str(target))
        self._write_delete_audit("run", run.run_id, True, target, collection_id=run.collection_id)
        return target

    def _write_delete_audit(self, target_type: str, target_id: str, delete_files: bool, moved_to: Path | None, collection_id: str | None = None) -> None:
        audit = self._trash_root() / "delete_audit.jsonl"
        payload = {
            "target_type": target_type,
            "collection_id": collection_id if target_type == "run" else target_id,
            "run_id": target_id if target_type == "run" else None,
            "delete_files": delete_files,
            "moved_to": str(moved_to) if moved_to else None,
            "deleted_at": utc_now(),
            "operator": "local",
        }
        with audit.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _write_corrupt_metadata_audit(self, path: Path, exc: Exception, line: int | None = None) -> None:
        audit = self._trash_root() / "corrupt_metadata_audit.jsonl"
        payload = {
            "path": str(path),
            "line": line,
            "error": str(exc),
            "detected_at": utc_now(),
            "operator": "local",
        }
        with audit.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _increment(self, run_id: str, key: str) -> None:
        try:
            record = self.get_run(run_id)
        except KeyError:
            return
        record.counts[key] = record.counts.get(key, 0) + 1
        record.updated_at = utc_now()
        self._write_run(record)

    def _recount(self, run_id: str) -> None:
        record = self.get_run(run_id)
        counts = {**record.counts, "pending": 0, "accepted": 0, "rejected": 0, "deleted": 0, "manual_review": 0}
        for image in self.list_images(run_id):
            counts[image.bucket] = counts.get(image.bucket, 0) + 1
        record.counts = counts
        record.updated_at = utc_now()
        self._write_run(record)


def _default_v3_runs_root() -> Path:
    app_shot_runs = os.environ.get("APP_SHOT_RUNS")
    if not app_shot_runs:
        return Path("runs/v3")
    root = Path(app_shot_runs)
    return root if root.name.lower() == "v3" else root / "v3"


def _default_obs_output_root() -> Path:
    explicit = os.environ.get("APP_SHOT_OBS_OUTPUT")
    if explicit:
        return Path(explicit)
    home = os.environ.get("APP_SHOT_HOME")
    if home:
        return Path(home) / "obs-output"
    return Path("obs-output")


def _collection_short_id(collection_id: str) -> str:
    tail = collection_id.rsplit("_", 1)[-1]
    return (tail or collection_id)[0:6]


def _safe_windows_name(value: str) -> str:
    cleaned = "".join("_" if char in '/\\:*?"<>|' else char for char in value.strip())
    cleaned = "_".join(part for part in cleaned.split() if part)
    cleaned = cleaned.strip(" ._")
    return cleaned[:40] or "collection"


def _game_agent_capabilities(config: V3TaskConfig) -> list[str]:
    capabilities: list[str] = []
    if config.allow_ui_click or config.enable_auto_click:
        capabilities.append("UI 点击")
    if config.allow_hotkeys:
        capabilities.append("热键探索")
    if config.allow_wasd:
        capabilities.append("WASD")
    if config.allow_mouse_look:
        capabilities.append("鼠标视角")
    if config.allow_back_close:
        capabilities.append("返回/关闭")
    if config.allow_inventory_map_explore:
        capabilities.append("地图/背包/仓库探索")
    if config.allow_training_movement:
        capabilities.append("训练场移动探索")
    return capabilities


def _action_blocked_reason(action: dict[str, object] | None) -> str | None:
    if not action:
        return None
    result = action.get("result", {})
    if isinstance(result, dict) and result.get("executed") is True:
        return None
    reason = action.get("blocked_reason")
    if reason:
        return str(reason)
    if isinstance(result, dict) and result.get("reason"):
        return str(result["reason"])
    return None


def _game_agent_status(config: V3TaskConfig, latest_action: dict[str, object] | None) -> str:
    if not config.enable_game_agent and not config.enable_game_explorer:
        return "未启用"
    reason = _action_blocked_reason(latest_action)
    if reason:
        return "被阻止"
    if latest_action:
        return "运行中"
    return "等待首帧"


def _count_meta_values(images: list[V3ImageRecord], key: str, default: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for image in images:
        value = str(image.meta.get(key) or default)
        counts[value] = counts.get(value, 0) + 1
    return counts


def _count_reject_reasons(images: list[V3ImageRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for image in images:
        if image.bucket != "rejected":
            continue
        reason = image.reject_reason or "unknown"
        counts[reason] = counts.get(reason, 0) + 1
    return counts


def _accepted_class_count(images: list[V3ImageRecord], class_name: str) -> int:
    return sum(1 for image in images if str(image.meta.get("accepted_class") or "") == class_name)


def _visual_fill_ratio(images: list[V3ImageRecord]) -> float:
    if not images:
        return 0.0
    return round(_accepted_class_count(images, "accepted_visual_fill") / len(images), 4)


def _top_reject_reason(images: list[V3ImageRecord]) -> str | None:
    distribution = _count_reject_reasons(images)
    if not distribution:
        return None
    return max(distribution.items(), key=lambda item: item[1])[0]


def _top_reject_reasons(images: list[V3ImageRecord], limit: int = 3) -> list[dict[str, object]]:
    distribution = _count_reject_reasons(images)
    return [
        {"reason": reason, "count": count}
        for reason, count in sorted(distribution.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def _collection_rejection_summary(images: list[V3ImageRecord]) -> dict[str, object]:
    return {
        "reject_reason_distribution": _count_reject_reasons(images),
        "duplicate_across_runs_total": sum(1 for image in images if image.reject_reason == "rejected_duplicate_across_runs"),
        "near_duplicate_total": sum(1 for image in images if image.reject_reason == "near_duplicate"),
    }


def _collection_status(collection: V3CollectionRecord, accepted_unique_total: int, has_running_run: bool) -> str:
    if collection.status == "deleted":
        return "deleted"
    if has_running_run:
        return "collecting"
    if collection.status == "stopped":
        return "stopped"
    config = collection.config
    if accepted_unique_total >= config.target_accepted_max:
        return "max_target_reached"
    if accepted_unique_total >= config.target_accepted_soft:
        return "soft_target_reached"
    if accepted_unique_total >= config.target_accepted_min:
        return "min_target_reached"
    if accepted_unique_total > 0:
        return "insufficient"
    return "not_started"


def _continue_suggestion(latest_round: dict[str, object] | None, accepted_unique_total: int, config: V3TaskConfig) -> str:
    if accepted_unique_total >= config.target_accepted_max:
        return "已达到最大扩充目标，建议停止采集并导出最终有效截图。"
    if accepted_unique_total >= config.target_accepted_soft:
        return "标准目标已达标，可继续扩充或导出最终有效截图。"
    if accepted_unique_total >= config.target_accepted_min:
        return f"小目标已达标，可继续冲标准目标 {config.target_accepted_soft}。"
    if not latest_round:
        return "尚未开始采集，请启动第一轮采集。"
    processed = int(latest_round.get("processed", 0) or 0)
    accepted = int(latest_round.get("accepted", 0) or 0)
    duplicate = int(latest_round.get("duplicate_across_runs", 0) or 0)
    new_unique = int(latest_round.get("new_unique", 0) or 0)
    if processed == 0:
        return "上一轮 OBS 输入不足，请检查 OBS 输出目录。"
    if accepted and duplicate / max(1, accepted) >= 0.35:
        return "上一轮重复率较高，建议切换软件页面、游戏场景、背包、地图、仓库、训练场区域后继续采集。"
    if accepted and new_unique / max(1, accepted) <= 0.25:
        return "上一轮有效图较少，建议手动切换场景后继续。"
    return "数量不足，需要继续采集；系统会自动跨轮去重并累计。"


def _image_signature(image: V3ImageRecord) -> dict[str, object]:
    ocr_text = ""
    ocr = image.meta.get("ocr")
    if isinstance(ocr, dict):
        boxes = ocr.get("text_boxes", [])
        if isinstance(boxes, list):
            texts = [str(box.get("text", "")) for box in boxes if isinstance(box, dict)]
            ocr_text = " ".join(texts).strip().casefold()
    return {
        "sha256": image.sha256,
        "content_hash": image.content_hash,
        "near_duplicate_signature": image.duplicate_decision.get("content_hash") or image.content_hash or image.sha256,
        "ocr_text_signature": ocr_text,
    }


def _find_collection_duplicate(rows: list[object], signature: dict[str, object], current_run_id: str | None = None) -> dict[str, object] | None:
    for row in rows:
        if not isinstance(row, dict):
            continue
        if current_run_id and row.get("run_id") == current_run_id:
            continue
        for key in ("sha256", "content_hash", "near_duplicate_signature"):
            value = signature.get(key)
            if value and row.get(key) == value:
                return row
        ocr_signature = signature.get("ocr_text_signature")
        if ocr_signature and row.get("ocr_text_signature") == ocr_signature:
            return row
    return None


def _slug(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned[:32] or "collection"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _duplicate_summary(images: list[V3ImageRecord]) -> dict[str, object]:
    reasons = [_duplicate_decision_reason(image) for image in images]
    return {
        "exact_duplicate_count": sum(1 for image in images if bool(image.duplicate_decision.get("exact_duplicate"))),
        "action_representative_accepted_count": sum(
            1
            for image in images
            if image.bucket == "accepted" and bool(image.duplicate_decision.get("accepted_as_action_representative"))
        ),
        "visual_difference_accepted_count": sum(1 for image, reason in zip(images, reasons) if image.bucket == "accepted" and reason == "visual_difference_accepted"),
        "menu_state_accepted_count": sum(1 for image, reason in zip(images, reasons) if image.bucket == "accepted" and "menu_state" in reason),
        "dialog_state_accepted_count": sum(1 for image, reason in zip(images, reasons) if image.bucket == "accepted" and "dialog_state" in reason),
        "periodic_static_rejected_count": sum(1 for reason in reasons if reason == "periodic_static_frame_rejected"),
        "duplicate_policy_summary": {
            "duplicate_algorithm": "sha256_exact",
            "duplicate_threshold": 1.0,
            "near_duplicate_enabled": True,
            "periodic_static_frames": "rejected",
            "action_representative_limit": 3,
        },
    }


def _duplicate_decision_reason(image: V3ImageRecord) -> str:
    decision = image.duplicate_decision or {}
    reason = decision.get("duplicate_decision_reason")
    return str(reason or image.reject_reason or "unknown")


def _folder_watch_metric(run_dir: Path, key: str, default: int) -> int:
    path = run_dir / "meta" / "folder_watch_summary.json"
    if not path.is_file():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
    value = payload.get(key, default)
    return value if isinstance(value, int) else default


def _folder_watch_object(run_dir: Path, key: str) -> dict[str, object]:
    path = run_dir / "meta" / "folder_watch_summary.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    value = payload.get(key, {})
    return value if isinstance(value, dict) else {}


def _count_action_statuses(actions: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in actions:
        result = action.get("result", {})
        if not isinstance(result, dict):
            continue
        status = result.get("status")
        if isinstance(status, str):
            counts[status] = counts.get(status, 0) + 1
    return counts


def _count_action_regions(actions: list[dict[str, object]]) -> dict[str, int]:
    counts = {
        "content_area_blocked": 0,
        "ui_chrome_click": 0,
        "unsafe_chrome_blocked": 0,
    }
    for action in actions:
        region = action.get("candidate_region_type")
        result = action.get("result", {})
        if not isinstance(result, dict):
            result = {}
        executed = result.get("executed") is True
        reason = str(result.get("reason") or action.get("blocked_reason") or "")
        if region == "content_area" and (not executed or reason == "content_area_not_clickable"):
            counts["content_area_blocked"] += 1
        elif region == "ui_chrome" and executed:
            counts["ui_chrome_click"] += 1
        elif region == "unsafe_chrome" and (not executed or reason == "unsafe_chrome"):
            counts["unsafe_chrome_blocked"] += 1
    return counts


def _action_executed(action: dict[str, object]) -> bool:
    result = action.get("result", {})
    return isinstance(result, dict) and result.get("executed") is True
