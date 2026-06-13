# P7: Master Backend + API

## Goal

P7 builds the backend control plane that unifies P0-P6 capabilities into a schedulable platform surface.

The stage covers:

- App management.
- Run lifecycle orchestration.
- Worker registration and heartbeat.
- Mock worker assignment decisions.
- Upload state flow orchestration.
- Model Gateway proxying through the existing P3 safety path.
- SQLite development persistence with PostgreSQL URL configuration readiness.

## Architecture

```text
FastAPI Layer
  -> Service Layer
  -> Repository Layer
  -> SQLite fallback / PostgreSQL-ready config
```

Repository classes are the only database entry point. Service classes do not write SQL.

## Implemented API Surface

App:

- `POST /api/apps`
- `GET /api/apps`
- `GET /api/apps/{app_id}`

Run:

- `POST /api/runs`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/runs/{run_id}/start`
- `GET /api/runs/{run_id}/summary`

Worker:

- `POST /api/workers/register`
- `GET /api/workers`
- `POST /api/workers/{worker_id}/heartbeat`

Upload mock orchestration:

- `POST /api/upload-manifest`
- `POST /api/confirm-upload`
- `POST /api/cleanup`
- `POST /api/finalize`

Model Gateway proxy:

- `POST /api/model/scene_classify`
- `POST /api/model/ground`
- `POST /api/model/act`

## Data Models

The P7 SQLite repository layer stores:

- apps
- runs
- workers
- images
- uploads

The run status flow reuses the P1-P5 `RunLifecycle` and `RunStatus` definitions.

## Boundaries

P7 does not implement:

- Worker execution logic.
- Screenshot capture.
- Behavior packs.
- Dedup or quality logic.
- Real model inference.
- UI.
- Worker Runtime.
- Four-machine deployment.
- Real OBS, FFmpeg, ADB, Playwright, or pywinauto integration.

## Development Mode

Development mode uses SQLite and a memory Redis fallback. PostgreSQL is represented at the configuration layer through `DATABASE_URL`, but P7 does not add a PostgreSQL driver dependency.

## Validation

```powershell
python -m pytest tests/unit/test_master_backend_api.py -q
python -m pytest -q
```
