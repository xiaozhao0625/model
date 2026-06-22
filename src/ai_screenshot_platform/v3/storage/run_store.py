from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from ai_screenshot_platform.v3.schemas import (
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

    def create_run(self, config: V3TaskConfig) -> V3RunRecord:
        run_id = f"v3_{utc_now().replace(':', '').replace('+', '_').replace('.', '_')}_{uuid.uuid4().hex[:8]}"
        display_name = config.display_name or config.task_name or config.app_name or run_id
        config.display_name = display_name
        record = V3RunRecord(
            run_id=run_id,
            config=config,
            task_name=config.task_name,
            app_name=config.app_name,
            display_name=display_name,
        )
        self._write_run(record)
        self.append_event(run_id, "run_created", {"observe_only": config.observe_only})
        return record

    def list_runs(self) -> list[V3RunRecord]:
        records: list[V3RunRecord] = []
        for path in sorted(self.root.glob("*/run.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            records.append(V3RunRecord.model_validate_json(path.read_text(encoding="utf-8")))
        return records

    def get_run(self, run_id: str) -> V3RunRecord:
        path = self._run_path(run_id)
        if not path.is_file():
            raise KeyError(f"v3 run not found: {run_id}")
        return V3RunRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def update_status(self, run_id: str, status: str, error: str | None = None) -> V3RunRecord:
        record = self.get_run(run_id)
        record.status = status  # type: ignore[assignment]
        record.updated_at = utc_now()
        record.last_error = error
        self._write_run(record)
        self.append_event(run_id, "status_changed", {"status": status, "error": error})
        return record

    def add_image(self, run_id: str, image: V3ImageRecord) -> V3ImageRecord:
        image_path = self._run_dir(run_id) / "images.jsonl"
        with image_path.open("a", encoding="utf-8") as file:
            file.write(image.model_dump_json() + "\n")
        self._recount(run_id)
        self.append_event(run_id, "image_added", {"image_id": image.image_id, "bucket": image.bucket})
        return image

    def list_images(self, run_id: str) -> list[V3ImageRecord]:
        path = self._run_dir(run_id) / "images.jsonl"
        if not path.is_file():
            return []
        return [V3ImageRecord.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

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
        return [V3Event.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

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
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

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

    def _write_run(self, record: V3RunRecord) -> None:
        path = self._run_path(record.run_id)
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

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
