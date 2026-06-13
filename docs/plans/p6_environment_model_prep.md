# P6: Environment Configuration And Model Deployment Prep

## Goal

P6 prepares deployment configuration for later Master Backend, Web Dashboard, Worker Runtime, real adapters, model download, and four-machine production rollout. It solves two planning needs:

- One development machine can simulate Master, Model Gateway, PC Game Worker, PC App/Web Worker, and Android Worker.
- Four production machines can be mapped to clear roles, capabilities, data roots, model roots, and service addresses.

## Completed Scope

- Added single-node development topology config.
- Added four-node production topology config.
- Added local development machine role config.
- Added four-machine production role config.
- Added role-specific env templates.
- Added model manifest example.
- Added topology validation script.
- Added model manifest validation script.
- Added local development environment check script.
- Added deployment docs for environment setup and model deployment planning.

## Architecture Rules

- P6 only prepares configuration and validation.
- No real model is downloaded.
- No model library is imported.
- No PostgreSQL, Redis, FastAPI, Worker, OBS, FFmpeg, ADB, Playwright, or pywinauto service is started.
- Runtime code must read addresses, model paths, machine roles, and worker capabilities from config.
- Single-node development and four-node production must switch by config, not by changing core code.
- Model paths must come from `model_manifest`.
- Lightweight models may be planned as resident.
- Heavy models must support on-demand loading.

## Single-Node Development Topology

`configs/topology/single_node_dev.example.json` models one physical development machine with these logical roles:

- `master`
- `model_gateway`
- `worker_pc_game_local`
- `worker_pc_app_web_local`
- `worker_android_local`

The workers include capabilities for high bucket game capture, low bucket PC app/web capture, and low bucket Android capture.

## Four-Node Production Topology

`configs/topology/four_node_prod.example.json` models:

- `M0`: Master + PostgreSQL + Redis + Model Gateway, RTX 5060 Ti 16GB.
- `W1`: PC Game Worker, RTX 3060 12GB.
- `W2`: PC App + Web Worker, RTX 3060 12GB.
- `W3`: Android Worker, RTX 3060 12GB.

## Model Manifest

`configs/model_gateway/model_manifest.example.json` declares:

- `ui_tars`
- `showui`
- `qwen_vl`
- `omniparser`
- `gui_actor`
- `os_atlas`

The manifest records target machine, local path, load mode, GPU need, VRAM budget, and notes. It does not require model files to exist.

## Validation Commands

```powershell
python -m pytest tests/unit/test_environment_configs.py -q
python -m pytest -q
python scripts/env/check_topology_config.py --config configs/topology/single_node_dev.example.json
python scripts/env/check_topology_config.py --config configs/topology/four_node_prod.example.json
python scripts/models/check_model_manifest.py --manifest configs/model_gateway/model_manifest.example.json
python scripts/env/check_local_dev_env.py
```

## Not In P6

- No real model download.
- No real model provider.
- No API or database schema.
- No UI.
- No Worker runtime scheduling.
- No real OBS, FFmpeg, ADB, Playwright, pywinauto, or OCR integration.
