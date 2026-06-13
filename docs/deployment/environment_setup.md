# Environment Setup

## Scope

P6 only prepares configuration, topology examples, environment templates, and local validation scripts. It does not start PostgreSQL, Redis, FastAPI, Worker processes, OBS, FFmpeg, ADB, Playwright, pywinauto, or any model service.

## Single-Node Development

Use `configs/topology/single_node_dev.example.json` when one development machine needs to simulate the full platform:

- master API
- model gateway
- PC game worker
- PC app / web worker
- Android worker

Each logical worker has its own `worker_id`, `worker_type`, `capabilities`, `data_root`, `master_url`, and `model_gateway_url`. The example uses `127.0.0.1`, but future runtime code must read service addresses from config or environment variables instead of hard-coding them.

Use `configs/machines/local_dev.example.json` to describe the current one-machine development role. This file allows one physical machine to host multiple logical workers for dry-run and integration checks.

## Four-Node Production

Use `configs/topology/four_node_prod.example.json` and `configs/machines/four_machine_roles.example.json` for the production shape:

- `M0`: Master + PostgreSQL + Redis + Model Gateway on RTX 5060 Ti 16GB.
- `W1`: PC Game Worker on RTX 3060 12GB.
- `W2`: PC App + Web Worker on RTX 3060 12GB.
- `W3`: Android Worker on RTX 3060 12GB.

The production topology maps each worker to a machine and records the worker capabilities, data roots, master URL, model gateway URL, and model root. Switching from single-node development to four-node production should be done by changing config files and environment variables, not by editing core code.

## Environment Templates

Role-specific templates live under `configs/env/`:

- `master.env.example`
- `model_gateway.env.example`
- `worker_pc_game.env.example`
- `worker_pc_app_web.env.example`
- `worker_android.env.example`

Across the templates, the required variable set is covered:

- `MASTER_URL`
- `MODEL_GATEWAY_URL`
- `DATA_ROOT`
- `MODEL_ROOT`
- `WORKER_ID`
- `WORKER_TYPE`
- `WORKER_CAPABILITIES`
- `DATABASE_URL`
- `REDIS_URL`
- `LOG_LEVEL`

Additional planning variables include `APP_ENV`, `NODE_ROLE`, `MACHINE_ID`, `RUN_ROOT`, `UPLOAD_EXPECTED_ROOT`, `MODEL_MANIFEST_PATH`, `SAFETY_LEXICON_PATH`, `BEHAVIOR_PACK_ROOT`, and `WORKER_HEARTBEAT_INTERVAL_SEC`.

## Validation Commands

Run these checks from the repository root:

```powershell
python scripts/env/check_topology_config.py --config configs/topology/single_node_dev.example.json
python scripts/env/check_topology_config.py --config configs/topology/four_node_prod.example.json
python scripts/env/check_local_dev_env.py
```

The checks only read local files and print JSON summaries. GPU information is optional and never blocks P6 validation.

## Development Boundary

P6 does not connect real infrastructure. PostgreSQL, Redis, Master API, Worker Runtime, model serving, and real tool adapters remain later-stage work.
