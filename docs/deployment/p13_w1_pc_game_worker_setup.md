# W1 PC Game Worker 部署步骤

## 目标

W1 承载 PC Game Worker，后续真实 high 桶采集必须走行为包 + OBS/FFmpeg 抽帧。P13 仅做真实工具健康检查和小规模 smoke，不做大规模采集。

## 手动准备

1. 安装 Python、Git、NVIDIA Driver。
2. 安装 OBS Studio。
3. 安装 FFmpeg，并确认 `ffmpeg` 可从 PATH 调用。
4. 可选安装 AutoHotkey，但默认不执行危险动作。
5. 克隆项目仓库。
6. 复制 `configs/deploy/w1_pc_game_worker.production.env.example` 为本机 `.env`。

## 环境重点

```text
MASTER_URL=http://<M0_LAN_IP>:8000
WORKER_ID=W1-PC-GAME
WORKER_TYPE=pc_game
CAPABILITIES=capture_high,behavior_pack,obs_capture,ffmpeg_extract
LOCAL_CAPTURE_ROOT=D:\runs\w1
```

## 启动

```powershell
scripts\deploy\p13\start_w1_pc_game_worker.bat
```

## 健康检查

```powershell
python scripts/deploy/p13/check_w1_pc_game_stack.py --master-url http://<M0_LAN_IP>:8000
```

## Smoke

1. 检查 OBS 是否可用。
2. 检查 obs-websocket 是否可连或明确 unavailable。
3. 检查 FFmpeg 是否可用。
4. 运行 PC Game Worker dry-run。
5. 生成 high 桶测试帧或明确 unavailable 原因。
6. 通过 Master API 写入 quality_report / diagnostics。
