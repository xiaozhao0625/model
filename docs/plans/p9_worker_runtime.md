# P9：Worker Runtime 与 Master/Worker 通信

## 阶段目标

P9 建立单机可验证的 Master/Worker 通信闭环：Master API 负责任务登记、Worker 注册、心跳、任务领取和结果上报；Worker Agent 负责任务领取后的 mock/stub 执行，并把 `WorkerResult` 上报回 Master。

本阶段只做本地运行时和通信合同，不接真实采集工具、不接真实模型、不做 UI、不做四机部署。

## 已完成内容

- 新增 Worker Agent 配置加载器，支持 `configs/workers/worker_agent.single_node_dev.example.json`。
- 新增 `MasterApiClient`，支持 `register_worker`、`send_heartbeat`、`claim_task`、`report_result`。
- 新增 `WorkerRuntime.start_once()`，按单轮流程执行：注册 -> 心跳 -> 领取任务 -> 执行 mock/stub -> 上报结果。
- 新增 `ExecutorResolver`，按 execution mode 复用 P4 的 `MockWorkerAgent`、PC Game stub、PC App stub、Web stub、Android stub 和 Behavior Worker。
- Master API 新增 canonical Worker 路由：
  - `POST /api/workers/{worker_id}/claim`
  - `POST /api/workers/{worker_id}/runs/{run_id}/report`
- Master 保存 run 的 `target_min` / `target_max`，便于 worker 按任务目标采集。
- Worker 上报结果后，Master 更新 run 状态和分桶计数，并将 Worker 置回 idle。
- 新增 P9 dry-run：`scripts/dev/mock_p9_master_worker_run.py`。

## 状态边界

- Worker 最多把 run 推进到 `capture_completed`。
- Worker 不进入 `upload_pending`、`uploaded_confirmed`、`local_deleted`、`completed`。
- Worker 不生成 `upload_manifest.json`。
- 上传、确认、清理和 completed 收口仍由 P2/P7 upload API 负责。

## 本地验证流

1. Master 创建 app 和 pending run。
2. Worker Agent 注册并发送 heartbeat。
3. Worker Agent 调用 claim 路由领取 pending run。
4. Master 将 run 合法推进到 `running`，并返回 `WorkerTask`。
5. Worker Agent 使用 mock/stub executor 复用 `LocalRunSession` 执行采集。
6. Worker Agent 上报 `WorkerResult`。
7. Master 更新 run 为 `capture_completed`，写入计数，并释放 Worker。

## 禁止事项

- 不接真实 OBS、FFmpeg、ADB、Playwright、pywinauto、AutoHotkey、pydirectinput、OCR。
- 不执行真实鼠标、键盘或系统动作。
- 不接真实模型库。
- 不新增依赖。
- 不做 UI。
- 不做四机部署和生产调度。
