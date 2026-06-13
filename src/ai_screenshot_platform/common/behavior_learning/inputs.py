from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class BehaviorLearningInputError(ValueError):
    pass


@dataclass(frozen=True)
class BehaviorLearningInput:
    app_id: str
    run_id: str
    game_type: str
    behavior_pack_id: str
    run_dir: str | Path
    summary_path: str | Path | None = None
    meta_path: str | Path | None = None
    run_log_path: str | Path | None = None
    behavior_actions_path: str | Path | None = None
    manual_seed_record_path: str | Path | None = None

    def resolve(self) -> BehaviorLearningInput:
        run_dir = Path(self.run_dir)
        return BehaviorLearningInput(
            app_id=self.app_id,
            run_id=self.run_id,
            game_type=self.game_type,
            behavior_pack_id=self.behavior_pack_id,
            run_dir=run_dir,
            summary_path=self.summary_path or run_dir / "summary.json",
            meta_path=self.meta_path or run_dir / "meta.jsonl",
            run_log_path=self.run_log_path or run_dir / "run.log",
            behavior_actions_path=self.behavior_actions_path
            or run_dir / "behavior_actions.jsonl",
            manual_seed_record_path=self.manual_seed_record_path
            or run_dir / "manual_seed_record.jsonl",
        )


@dataclass(frozen=True)
class BehaviorLearningSnapshot:
    summary: dict
    meta_rows: list[dict]
    run_events: list[dict]
    behavior_actions: list[dict]
    manual_seed_events: list[dict] | None = None


class BehaviorLearningInputReader:
    def __init__(
        self,
        learning_input: BehaviorLearningInput,
        allow_missing_behavior_actions: bool = False,
    ) -> None:
        self.learning_input = learning_input.resolve()
        self.allow_missing_behavior_actions = allow_missing_behavior_actions

    def read(self) -> BehaviorLearningSnapshot:
        summary = self._read_json(Path(self.learning_input.summary_path))
        meta_rows = self._read_jsonl(Path(self.learning_input.meta_path))
        run_events = self._read_jsonl(Path(self.learning_input.run_log_path))
        behavior_actions_path = Path(self.learning_input.behavior_actions_path)
        if behavior_actions_path.exists():
            behavior_actions = self._read_jsonl(behavior_actions_path)
        elif self.allow_missing_behavior_actions:
            behavior_actions = []
        else:
            raise BehaviorLearningInputError(
                f"behavior_actions.jsonl not found: {behavior_actions_path}"
            )

        manual_seed_path = Path(self.learning_input.manual_seed_record_path)
        manual_seed_events = (
            self._read_jsonl(manual_seed_path) if manual_seed_path.exists() else []
        )
        return BehaviorLearningSnapshot(
            summary=summary,
            meta_rows=meta_rows,
            run_events=run_events,
            behavior_actions=behavior_actions,
            manual_seed_events=manual_seed_events,
        )

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise BehaviorLearningInputError(f"required file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise BehaviorLearningInputError(f"invalid JSON file: {path}") from exc

    def _read_jsonl(self, path: Path) -> list[dict]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError as exc:
            raise BehaviorLearningInputError(f"required file not found: {path}") from exc
        rows = []
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise BehaviorLearningInputError(
                    f"invalid JSONL at {path}:{line_number}"
                ) from exc
        return rows
