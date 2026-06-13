# 项目进度看板

## 当前阶段

当前已完成 P12：行为包自我深化引擎。下一阶段为 P13：四机部署、分布式调度、并发压测。

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| P0 项目基线与开发治理 | done | 已建立项目文档、阶段计划、Codex 工作协议和架构基线。 |
| P1 MVP 基础框架 | done | 已完成分桶、去重、summary/meta、状态机、LocalRunSession 和 dry-run。 |
| P2 本地暂存、上传确认、清理流 | done | 已完成 upload_manifest、upload_record、local_deleted、completed 和状态恢复。 |
| P3 模型网关 | done | 已完成合同层、Mock/Stub Provider、风险词表、安全网关、审计日志和 dry-run。 |
| P4 多类型 Worker 与行为包 | done | 已完成 Worker 合同、Behavior Pack、PC Game/PC App/Web/Android stub pipeline 和 dry-run。 |
| P5 补采机制与人工补种子 | done | 已完成 CoverageManager、RetryPolicy、Manual Seed Gate、failed_low_yield 和 dry-run。 |
| P6 环境配置与模型部署预备 | done | 已完成单机/四机拓扑、机器角色、env 模板、模型 manifest、检查脚本和部署文档。 |
| P7 Master Backend + PostgreSQL/SQLite + API | done | 已完成 Master API、SQLite/PostgreSQL 边界、run-scoped upload canonical routes 和 smoke 测试。 |
| P8 Web Dashboard UI 控制台 | done | 已完成中文 Web Console、暗色工业控制台、明暗主题切换和构建验收。 |
| P9 Worker Runtime 与 Master/Worker 通信 | done | 已完成单机 Worker HTTP 进程边界、注册、心跳、claim/report 和 mock/stub runtime。 |
| P10 真实采集适配器接入 | done | 已完成真实采集适配器边界、可选工具健康检查、smoke 脚本和 stub fallback。 |
| P11 模型拉取、模型部署、真实 Provider 接入 | done | 已完成模型 manifest、下载计划、Provider runtime、真实 Provider 边界和 optional smoke。 |
| P12 行为包自我深化引擎 | done | 已完成离线输入读取、指标计算、FPS/MOBA 分析、候选包生成、人工审核、回滚和 dry-run。 |
| P13 四机部署、分布式调度、并发压测 | next | 后续进入生产化部署与并发压测阶段。 |

## 当前架构基线

- bucket 只有 `fixed`、`low`、`high`、`rejected`。
- `fixed` 可选，最多 10 张。
- `low` 或 `high` 至少出现一种。
- `valid_total = fixed + low + high`。
- `rejected` 和 duplicate 不计入 `valid_total`。
- `valid_total >= 1000` 且存在 low/high 后才能进入 `capture_completed`。
- `valid_total <= 5000`；达到上限后停止继续采集，但不新增 `completed_max` 状态。
- `capture_completed -> upload_pending -> uploaded_confirmed -> local_deleted -> completed` 是上传清理主路径。
- 用户确认已上传百度网盘后，才能进入 `uploaded_confirmed`。
- 只有 `uploaded_confirmed` 后才允许删除本地图片和临时视频，并进入 `local_deleted`。
- 删除后必须保留 `summary.json`、`meta.jsonl`、`upload_manifest.json`、`upload_record.json`、`cleanup_record.json`、`run.log`。
- Worker 必须复用 `LocalRunSession`，不重复实现截图分桶、去重、summary、状态流。
- PC 游戏 high 桶必须使用行为包 + OBS/FFmpeg 抽帧；当前真实工具均保持可选、可跳过。
- AI 只做低频决策，只能返回 `ActionProposal`，不直接执行动作。
- 禁止自动处理验证码、支付、充值、购买、聊天发送、账号安全验证、反作弊绕过。
- app-screenshot-agent 只作为 Android Worker 和公共质量模块的复用来源，不整体替代新平台架构。
- P12 行为包学习仅读取离线记录，输出候选包默认 `pending_review`，不自动启用、不训练模型、不修改原始 run 产物。

## 风险与阻塞

| 风险 | 当前处理 |
| --- | --- |
| 真实工具环境差异大 | P10 已将真实工具接入做成可选健康检查与 stub fallback。 |
| 真实模型体积和 GPU 要求不确定 | P11 只做 manifest、路径解析和 optional provider 边界，不强制下载或加载模型。 |
| 行为包候选误启用 | P12 候选包默认 `pending_review`，必须人工审核，支持拒绝和回滚记录。 |
| 历史 run 产物被误改 | P12 输入读取保持只读，学习输出写入独立 `behavior_learning/{app_id}/{run_id}/` 目录。 |
