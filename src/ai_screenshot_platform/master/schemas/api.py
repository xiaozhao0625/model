from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AppCreateRequest(BaseModel):
    app_id: str
    name: str
    type: str
    platform: str


class RunCreateRequest(BaseModel):
    run_id: str
    app_id: str
    target_min: int = 1000
    target_max: int = 5000


class WorkerRegisterRequest(BaseModel):
    worker_id: str
    type: str
    machine_name: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class WorkerResultReportRequest(BaseModel):
    app_id: str
    run_id: str
    status: str
    valid_total: int
    fixed_count: int
    low_count: int
    high_count: int
    rejected_count: int
    run_dir: str
    summary_path: str
    error: str | None = None
    behavior_pack_id: str | None = None
    behavior_actions_path: str | None = None


class UploadRunRequest(BaseModel):
    run_id: str


class SceneClassifyApiRequest(BaseModel):
    app_id: str
    run_id: str
    screenshot_path: str
    context: dict[str, Any] = Field(default_factory=dict)


class GroundApiRequest(BaseModel):
    app_id: str
    run_id: str
    screenshot_path: str
    target_description: str
    context: dict[str, Any] = Field(default_factory=dict)


class ActApiRequest(BaseModel):
    app_id: str
    run_id: str
    screenshot_path: str
    scene_class: str
    instruction: str
    target_description: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
