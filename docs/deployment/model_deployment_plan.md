# Model Deployment Plan

## Scope

P6 defines the model deployment plan and manifest shape only. It does not download model files, import model libraries, start model services, or connect real providers.

## Model Root

The example manifest uses `models/` as the model repository root. This directory is ignored by git and is reserved for later P11 model downloads or local model placement.

The manifest file is:

```text
configs/model_gateway/model_manifest.example.json
```

Future runtime code must read model paths from the manifest. It must not hard-code drive letters, machine names, or local model paths.

## Manifest Entries

The P6 manifest includes these planned providers:

- `ui_tars`
- `showui`
- `qwen_vl`
- `omniparser`
- `gui_actor`
- `os_atlas`

Each entry declares:

- `model_id`
- `provider_type`
- `display_name`
- `target_machine`
- `local_path`
- `enabled_by_default`
- `load_mode`
- `gpu_required`
- `vram_budget_gb`
- `health_check_mode`
- `notes`

`load_mode` is limited to `resident` or `on_demand`.

## Resident And On-Demand Strategy

Lightweight helpers such as `showui` and `omniparser` may be planned as resident where appropriate. Heavier or backup models such as `ui_tars`, `qwen_vl`, `gui_actor`, and `os_atlas` are planned as on-demand.

RTX 5060 Ti 16GB and RTX 3060 12GB machines cannot safely assume all models are resident in VRAM at the same time. The manifest therefore records a `vram_budget_gb` for each model and keeps heavy models disabled by default until P11 introduces real loading and provider integration.

## Machine Placement

- `ui_tars`: primary GUI agent and low-frequency decision provider, preferred on M0 with quantized or on-demand loading.
- `showui`: lightweight coordinate grounding helper, suitable for W2 or M0.
- `qwen_vl`: general visual understanding, suitable for M0 or W3 on demand.
- `omniparser`: UI structure parsing for PC app and web screenshots, suitable for W2 or M0.
- `gui_actor`: backup GUI grounding provider, on demand.
- `os_atlas`: cross-platform GUI grounding backup, on demand.

PC Game Worker should prioritize game rendering, OBS recording, and FFmpeg extraction stability. It should not keep large GUI models resident unless a later architecture decision explicitly allows it.

## Validation

Validate the manifest with:

```powershell
python scripts/models/check_model_manifest.py --manifest configs/model_gateway/model_manifest.example.json
```

The validation checks manifest structure only. It intentionally does not require real model files to exist.

## Later Stage Boundary

P11 is the first stage that may download models and connect real provider implementations. P6 only prepares the manifest, placement policy, and validation script.
