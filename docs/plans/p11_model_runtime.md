# P11：模型拉取、模型部署、真实 Provider 接入

## 阶段目标

P11 建立 Model Gateway 的真实模型接入边界：模型 manifest、模型路径解析、模型文件健康检查、Provider runtime 配置、真实 Provider 边界、下载计划脚本和可选 smoke。P11 不下载模型，不要求 GPU，不强制安装 `torch` / `transformers`，没有模型文件时必须 fallback 到 mock。

## 模型 Manifest

`configs/model_gateway/model_manifest.example.json` 已补强为 P11 manifest，包含：

- `ui_tars`
- `showui`
- `qwen_vl`
- `omniparser`
- `gui_actor`
- `os_atlas`

每个模型条目包含 `expected_files`、`download`、`runtime`、`load_mode`、`gpu_required`、`vram_budget_gb` 等字段。`load_mode` 仅允许 `resident`、`on_demand`、`disabled`。

## Provider Runtime

`configs/model_gateway/provider_runtime.example.json` 默认：

- `default_provider=mock`
- `fallback_provider=mock`
- `enabled_providers=["mock"]`
- `allow_gpu=false`
- `allow_cpu_fallback=true`
- `max_loaded_models=1`

真实 provider 后续可按需启用，但默认不会加载真实模型。

## Fallback 策略

`ModelRuntimeManager.select_provider(...)` 优先检查默认 provider。默认真实模型不可用或未启用时，返回 fallback mock provider。Model Gateway 的 `RiskRuleDetector + SafetyGate` 保持生效，高风险 instruction 仍返回 `request_manual`。

## 可选真实 Smoke

`scripts/dev/smoke_model_gateway_optional.py` 会创建 runtime manager 和 ModelGatewayService。缺真实模型时使用 mock fallback，输出 `fallback_used=true`，不会失败。

## P11 不做事项

- 不下载模型。
- 不提交模型文件。
- 不强制安装 `torch`、`transformers`、CUDA 或 GPU 驱动。
- 不让 Master Backend 加载模型。
- 不让 PC Game Worker 常驻大模型。
- 不做模型微调、在线学习或四机部署。

## P11 与 P13 的关系

P11 只建立单机模型 runtime 和 Provider 边界。P13 才处理四机部署、分布式调度、并发压测和生产化模型资源编排。
