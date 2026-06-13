# 真实采集工具可选安装说明

P10 默认不要求安装任何真实采集工具。以下工具只用于可选 smoke test，缺失时 `scripts/dev/check_real_tools.py` 会报告 unavailable，普通 pytest 仍应通过。

## Playwright

用于 Web Worker 真实网页内容区截图。

可选安装：

```bash
pip install playwright
python -m playwright install chromium
```

验证：

```bash
python scripts/dev/smoke_web_playwright_capture.py
```

## pywinauto / mss / dxcam

用于 PC 普通软件窗口聚焦和内容区域截图。

可选安装：

```bash
pip install pywinauto mss dxcam
```

P10 不默认执行真实窗口操作；真实适配器必须通过配置显式启用。

## OBS / obs-websocket

用于 PC Game high 桶录制入口检测。P10 只建立适配器和健康检查，不要求真实游戏运行。

可选准备：

- 安装 OBS Studio。
- 启用 obs-websocket。
- 安装 Python 客户端：`pip install obsws-python`。

验证：

```bash
python scripts/dev/smoke_pc_game_obs_ffmpeg.py
```

## FFmpeg

用于 PC Game 录制视频抽帧。

可选准备：

- 安装 FFmpeg。
- 确保 `ffmpeg` 在 PATH 中。

P10 默认不需要真实视频；没有视频时 smoke 只报告工具状态。

## ADB

用于 Android Worker 真实设备截图入口。

可选准备：

- 安装 Android platform-tools。
- 确保 `adb` 在 PATH 中。
- 按需启动模拟器或连接设备。

验证：

```bash
python scripts/dev/smoke_android_adb_capture.py
```

## 重要边界

- 这些工具均为可选真实 smoke，不是默认测试要求。
- 真实工具必须在 Worker 侧启用，不进入 Master。
- 真实采集不得处理验证码、支付、充值、购买、聊天发送、账号安全验证或反作弊绕过。
