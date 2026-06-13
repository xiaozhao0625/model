# 模型运行时可选部署说明

P11 默认不要求下载任何模型，也不要求安装模型依赖。以下步骤只用于后续真实 Provider smoke。

## MODEL_ROOT

默认模型根目录为仓库下的 `models/`。可以通过环境变量覆盖：

```bash
set MODEL_ROOT=D:\models\ai-screenshot-platform
```

Linux/macOS：

```bash
export MODEL_ROOT=/data/models/ai-screenshot-platform
```

manifest 中的 `models/showui` 会解析为 `$MODEL_ROOT/showui`。

## 模型文件检查

```bash
python scripts/models/check_model_files.py --manifest configs/model_gateway/model_manifest.example.json
```

缺文件时会输出 `status=missing_files`，不会失败。

## Runtime 检查

```bash
python scripts/models/check_model_runtime.py
```

该命令只检查 manifest、provider runtime 和 fallback，不加载真实模型。

## 下载计划

```bash
python scripts/models/plan_model_downloads.py
```

默认 dry-run，不访问网络，不依赖 `huggingface_hub` 或 `git-lfs`。如需写出计划：

```bash
python scripts/models/plan_model_downloads.py --write-plan runs/model_download_plan.json
```

## 手动放置模型

后续真实 smoke 前，可按 manifest 的 `download.url_or_hint` 手动下载模型，并放到：

- `$MODEL_ROOT/showui`
- `$MODEL_ROOT/omniparser`
- `$MODEL_ROOT/qwen_vl`
- `$MODEL_ROOT/ui_tars`
- `$MODEL_ROOT/gui_actor`
- `$MODEL_ROOT/os_atlas`

每个目录至少应包含 manifest 中声明的 `expected_files`。

## 显存策略

- 5060Ti 16GB 不假设所有模型同时常驻。
- 3060 12GB 优先保障 Worker 采集工具与系统稳定性。
- PC Game Worker 不常驻大模型。
- 重模型优先 `on_demand`。
- 建议先试 ShowUI / OmniParser，再试 Qwen-VL / UI-TARS。

## 可选 Provider 优先级

1. ShowUI 或 OmniParser：优先轻量定位/解析。
2. Qwen-VL：通用视觉理解，资源要求更高。
3. UI-TARS：主 GUI Agent，集成复杂度更高。
4. GUI-Actor / OS-Atlas：备用 grounding provider。
