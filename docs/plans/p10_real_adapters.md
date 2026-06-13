# P10：真实采集适配器接入

## 阶段目标

P10 将 P4/P9 的 mock/stub Worker 能力升级为真实采集适配器入口。本阶段不追求真实采集全量跑满，而是建立生产级边界：真实工具在 Worker 侧延迟导入、显式启用、可健康检查、可跳过，并且默认测试环境缺少工具时仍能通过。

## 真实工具接入边界

- Master 只负责任务调度、状态管理和结果接收，不导入 OBS、FFmpeg、ADB、Playwright、pywinauto、mss、dxcam 等采集工具。
- Worker Agent 通过 HTTP 与 Master 通信，支持独立进程 once 模式。
- Worker 执行仍复用 `LocalRunSession`、P4 pipeline 和 P9 `WorkerRuntime`。
- Worker 最多推进到 `capture_completed`，不进入 `upload_pending`、`uploaded_confirmed`、`local_deleted`、`completed`。
- 真实工具失败必须返回明确 unavailable / skipped / error，不静默吞掉。

## 可选工具

- Web：Playwright，用于网页内容区截图，默认 `content_area_only=true`。
- PC App：pywinauto、mss、dxcam，用于窗口聚焦和内容区域截图。
- PC Game：OBS / obs-websocket、FFmpeg，保持 high 桶行为包 + OBS/FFmpeg 抽帧路线。
- Android：ADB，作为 app-screenshot-agent 能力复用入口，不复制旧仓库。

## 缺少工具时如何跳过

`scripts/dev/check_real_tools.py` 会输出 JSON 诊断结果。每项包含 `available`、`version`、`reason`、`required_for`。默认配置 `configs/workers/real_adapters.example.json` 使用 stub 或 disabled，因此没有真实工具时全量 pytest 不会失败。

可选 smoke 脚本在工具缺失时输出 `skipped`，不会异常退出。

## P10 与 P13 的区别

P10 只做单机开发环境下的真实适配器边界、健康检查和可选 smoke。P13 才处理四机部署、分布式调度、并发压测和生产化稳定性。

## 不做事项

- 不下载模型。
- 不接真实模型库。
- 不做 UI。
- 不做四机部署。
- 不绕过验证码、支付、账号安全验证或反作弊。
- 不新增正式 RunStatus。
