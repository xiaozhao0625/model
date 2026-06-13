# W2 PC App / Web Worker 部署步骤

## 目标

W2 承载 PC App / Web Worker。Web Worker 必须只采集网页有效内容区，不采集浏览器地址栏、标签栏或 Windows 任务栏。普通 PC 软件默认进入 low 桶。

## 手动准备

1. 安装 Python、Git、NVIDIA Driver。
2. 安装 Playwright browsers。
3. 安装 pywinauto、mss、dxcam 等真实采集依赖。
4. 克隆项目仓库。
5. 复制 `configs/deploy/w2_pc_app_web_worker.production.env.example` 为本机 `.env`。

## 环境重点

```text
MASTER_URL=http://<M0_LAN_IP>:8000
WORKER_ID=W2-PC-APP-WEB
WORKER_TYPE=pc_app_web
CAPABILITIES=capture_low,playwright,pywinauto,mss,dxcam
LOCAL_CAPTURE_ROOT=D:\runs\w2
WEB_CONTENT_AREA_ONLY=true
```

## 启动

```powershell
scripts\deploy\p13\start_w2_pc_app_web_worker.bat
```

## 健康检查

```powershell
python scripts/deploy/p13/check_w2_pc_app_web_stack.py --master-url http://<M0_LAN_IP>:8000
```

## Smoke

1. 检查 Playwright browser 是否可用。
2. 执行 Web page screenshot smoke。
3. 验证 browser content-only gate。
4. 检查 pywinauto / mss / dxcam 可用性。
5. 生成 low 桶测试帧或明确 unavailable 原因。
6. 写入 quality_report / diagnostics。
