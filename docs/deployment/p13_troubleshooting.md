# P13 故障排查表

## PostgreSQL 连接失败

- 现象：smoke 输出 `postgres_available=false`。
- 可能原因：PostgreSQL 未启动、端口错误、用户权限不足、`DATABASE_URL` 无效。
- 检查命令：`python scripts/master/smoke_postgres_connection.py`。
- 解决步骤：确认服务启动、数据库存在、用户有权限、`.env` 使用占位符替换后的真实值仅保存在本机。
- 回传日志：smoke JSON 输出，删除敏感字段后回传。

## Redis 未启动

- 现象：Master health 正常但调度或缓存相关检查 unavailable。
- 可能原因：Redis 未启动或 `REDIS_URL` 错误。
- 检查命令：`python scripts/deploy/p13/check_m0_master_stack.py`。
- 解决步骤：启动 Redis，确认端口和 URL。
- 回传日志：M0 health check JSON。

## Master API 无法访问

- 现象：Worker 注册失败，Web Console fallback。
- 可能原因：Master API 未启动、防火墙阻止、`MASTER_URL` 错误。
- 检查命令：`curl http://<M0_LAN_IP>:8000/health`。
- 解决步骤：启动 Master API，开放端口，修正 Worker `.env`。
- 回传日志：Master API 日志、Worker 注册日志。

## Web Console 仍显示 mock 数据

- 现象：控制台数据不随 PostgreSQL 写入变化。
- 可能原因：`VITE_MASTER_API_URL` 错误、Master API 跨域或网络失败。
- 检查命令：浏览器开发者工具 Network，访问 `/api/quality-reports`。
- 解决步骤：修正 Web Console API URL，确认 Master API 可访问。
- 回传日志：浏览器 Network 错误截图、Web Console 构建配置。

## Worker 无法注册

- 现象：Dashboard 看不到 W1/W2/W3。
- 可能原因：Worker `.env` 中 `MASTER_URL`、`WORKER_ID` 或 `CAPABILITIES` 配置错误。
- 检查命令：对应 `check_w*_*.py`。
- 解决步骤：修正 `.env`，确认网络到 M0 可达。
- 回传日志：worker.log、health check JSON。

## 防火墙阻止端口

- 现象：本机可访问 M0，其他机器不可访问。
- 可能原因：Windows 防火墙未放行 Master API 端口。
- 检查命令：`python scripts/deploy/p13/check_four_machine_network.py --master-url http://<M0_LAN_IP>:8000`。
- 解决步骤：开放 Master API 端口，仅允许可信内网访问。
- 回传日志：network check JSON。

## OBS 无法连接

- 现象：W1 OBS health unavailable。
- 可能原因：OBS 未安装、obs-websocket 未启用、端口错误。
- 检查命令：`python scripts/deploy/p13/check_w1_pc_game_stack.py`。
- 解决步骤：启动 OBS，启用 websocket，确认端口。
- 回传日志：W1 health check JSON、OBS 日志。

## FFmpeg 不在 PATH

- 现象：W1 FFmpeg check unavailable。
- 可能原因：未安装或 PATH 未配置。
- 检查命令：`ffmpeg -version`。
- 解决步骤：安装 FFmpeg 并加入 PATH。
- 回传日志：命令输出摘要。

## Playwright 浏览器未安装

- 现象：W2 Playwright smoke 失败。
- 可能原因：浏览器包未安装。
- 检查命令：`python -m playwright install --dry-run`。
- 解决步骤：按官方文档安装浏览器。
- 回传日志：W2 health check JSON。

## pywinauto 权限问题

- 现象：窗口可见但无法定位或操作。
- 可能原因：目标应用以管理员权限运行，Worker 权限不足。
- 检查命令：W2 health check。
- 解决步骤：统一权限级别，必要时以管理员运行 Worker。
- 回传日志：worker.log、目标应用权限说明。

## mss/dxcam 截图失败

- 现象：PC App/Web 截图为空或失败。
- 可能原因：显示器不可见、远程桌面黑屏、驱动限制。
- 检查命令：W2 smoke。
- 解决步骤：确认桌面会话可见，切换截图 backend。
- 回传日志：quality_report、smoke_report。

## ADB 不识别设备

- 现象：`adb devices` 无设备。
- 可能原因：platform-tools 未配置、模拟器未启动、USB 授权未确认。
- 检查命令：`adb devices`。
- 解决步骤：启动模拟器，确认授权，修正 `ADB_SERIAL`。
- 回传日志：W3 health check JSON。

## uiautomator dump 失败

- 现象：Android UI dump unavailable。
- 可能原因：设备锁屏、应用无响应、系统权限限制。
- 检查命令：`adb shell uiautomator dump`。
- 解决步骤：解锁设备，重启目标应用或模拟器。
- 回传日志：adb 命令输出。

## Android screencap 黑屏

- 现象：截图为黑屏。
- 可能原因：目标应用 DRM、模拟器图形设置、远程会话问题。
- 检查命令：Android smoke。
- 解决步骤：切换模拟器渲染模式或记录 skipped/unavailable。
- 回传日志：quality_report、android_runtime。

## quality_report 未写入 PostgreSQL

- 现象：Web Console 质量报告为空。
- 可能原因：Master API ingest 失败、数据库 schema 未初始化。
- 检查命令：`python scripts/master/smoke_postgres_connection.py`。
- 解决步骤：确认 API 返回成功，确认 PostgreSQL schema ready。
- 回传日志：API 响应、smoke JSON。

## diagnostics 收集失败

- 现象：zip 未生成。
- 可能原因：输出目录权限不足。
- 检查命令：`python scripts/deploy/p13/collect_diagnostics.py --machine M0 --output runs/diagnostics`。
- 解决步骤：更换输出目录，确认磁盘空间。
- 回传日志：脚本 stderr/stdout。
