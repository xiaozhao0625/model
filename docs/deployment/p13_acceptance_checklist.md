# P13 验收清单

## M0

- [ ] PostgreSQL 可用。
- [ ] Redis 可用或有明确 fallback 说明。
- [ ] Master API `/health` 成功。
- [ ] Web Console 可访问。
- [ ] PostgreSQL smoke 通过。
- [ ] Production readiness API 可写入 PostgreSQL。

## Worker

- [ ] W1/W2/W3 能注册到 M0。
- [ ] 三台 Worker 心跳正常。
- [ ] Worker 不直连数据库。
- [ ] Worker 日志不打印完整 `DATABASE_URL` 或密码。

## 工具

- [ ] W1 OBS/FFmpeg health check 可运行。
- [ ] W2 Playwright/pywinauto/mss/dxcam health check 可运行。
- [ ] W3 ADB/Android emulator health check 可运行。
- [ ] 不可用工具有明确 unavailable/skipped 原因。

## 采集 smoke

- [ ] Web content-only smoke 不包含浏览器地址栏、标签栏或任务栏。
- [ ] Android 能 adb screencap 和 ui dump，或明确 skipped/unavailable 原因。
- [ ] PC Game 能 OBS/FFmpeg 产出 high 桶测试帧，或明确 unavailable 原因。
- [ ] PC App/Web 能产出 low 桶测试帧，或明确 unavailable 原因。

## 生产验收数据

- [ ] quality_report 可写入 PostgreSQL。
- [ ] ocr_report 可写入 PostgreSQL。
- [ ] tool_health 可写入 PostgreSQL。
- [ ] diagnostics 可写入 PostgreSQL。
- [ ] Web Console 显示真实 API 数据，不只是 mock fallback。

## 安全边界

- [ ] 上传清理流仍必须人工确认上传后才能删除本地文件。
- [ ] 不训练模型。
- [ ] 不下载大模型。
- [ ] 不做大规模生产采集。
- [ ] 不绕过验证码、支付、充值、购买、聊天发送、账号安全验证或反作弊。
