# P13 Diagnostics 收集方案

## 目标

当四机部署或 smoke 失败时，用户运行 diagnostics 收集脚本，将必要信息打包回传给架构师排查。脚本不收集 `.env` 明文，不收集数据库密码，不打印完整 `DATABASE_URL`。

## 命令

```powershell
python scripts/deploy/p13/collect_diagnostics.py --machine M0 --output runs/diagnostics
python scripts/deploy/p13/collect_diagnostics.py --machine W1 --output runs/diagnostics
python scripts/deploy/p13/collect_diagnostics.py --machine W2 --output runs/diagnostics
python scripts/deploy/p13/collect_diagnostics.py --machine W3 --output runs/diagnostics
```

## 输出

- `diagnostics_M0.zip`
- `diagnostics_W1.zip`
- `diagnostics_W2.zip`
- `diagnostics_W3.zip`

## 收集内容

- `machine_ready.json`
- `worker_ready.json`
- `tool_health.json`
- `android_runtime.json`
- `quality_report.json`
- `ocr_report.json`
- `smoke_report.json`
- `run.log`
- `worker.log`
- `master.log`
- git commit
- Python version
- Node version
- nvidia-smi 摘要

文件不存在时记录 `missing`，不失败。

## 不收集

- `.env`
- 数据库密码
- 完整 `DATABASE_URL`
- 安装包或大二进制文件
- 本地截图、视频、模型权重
