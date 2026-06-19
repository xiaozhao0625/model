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
        record = V3RunRecord(run_id=run_id, config=config)
        self._write_run(record)
        self.append_event(run_id, "run_created", {"observe_only": config.observe_only})
        return record

    def list_runs(self) -> list[V3RunRecord]:
        records: list[V3RunRecord] = []
        for path in sorted(self.root.glob("*/run.json")):
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

    def write_artifact(self, run_id: str, name: str, payload: object) -> Path:
        path = self._run_dir(run_id) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def summary(self, run_id: str, ocr_ready: bool, model_ready: bool, safety_gate_ready: bool) -> V3Summary:
        record = self.get_run(run_id)
        events = self.list_events(run_id)
        auto_ready = (
            ocr_ready
            and model_ready
            and safety_gate_ready
            and not record.config.observe_only
            and record.config.enable_auto_click
        )
        summary = V3Summary(
            run_id=run_id,
            status=record.status,
            counts=record.counts,
            observe_only=record.config.observe_only,
            auto_click_ready=auto_ready,
            model_ready=model_ready,
            ocr_ready=ocr_ready,
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
