# 项目进度看板

## 当前阶段

当前已完成 P12.5.1：Web Console 生产验收最小入口补丁。下一阶段仍为 P13：四机部署、分布式调度、并发压测。

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
| P12.5-P13Prep 生产采集就绪强化 | done | 已完成 OCR 公共能力、Quality Gate、Capture Core、Android 模拟器 optional runtime 和四机部署材料预备。 |
| P12.5.1 Web Console 生产验收最小入口 | done | 已新增质量报告、OCR 状态、行为包候选、工具健康四个最小可视化入口，均支持 mock fallback。 |
| P13 四机部署、分布式调度、并发压测 | next | 后续进入生产化部署与并发压测阶段。 |

## 当前架构基线

- bucket 只有 `fixed`、`low`、`high`、`rejected`。
- `fixed` 可选，最多 10 张。
- `low` 或 `high` 至少出现一种。
- `valid_total = fixed + low + high`。
- `rejected` 和 duplicate 不计入 `valid_total`。
- `capture_completed -> upload_pending -> uploaded_confirmed -> local_deleted -> completed` 是上传清理主路径。
- Worker 必须复用 `LocalRunSession`，不重复实现截图分桶、去重、summary、状态流。
- PC 游戏 high 桶必须使用行为包 + OBS/FFmpeg 抽帧；真实工具均保持可选、可跳过。
- AI 只做低频决策，只能返回 `ActionProposal`，不直接执行动作。
- 禁止自动处理验证码、支付、充值、购买、聊天发送、账号安全验证、反作弊绕过。
- P12 行为包学习输出候选包默认 `pending_review`，不自动启用、不训练模型、不修改原始 run 产物。
- P12.5-P13Prep 默认 OCR 为 disabled/mock，真实 OCR、ADB、OBS、FFmpeg、Playwright、pywinauto 均 optional/skipped。
- P12.5.1 只补 Web Console 验收入口，不改核心状态流、不进入 P13。
# P12.5.2 更新：PostgreSQL-backed Production Readiness Console API

- P12.5.2 已补齐 Master API 生产验收数据接口，覆盖质量报告、OCR 报告、工具健康、Android runtime、行为包候选审核和部署诊断。
- 默认开发/测试仍使用 SQLite；生产可通过 `DATABASE_URL` 切换 PostgreSQL。
- Worker 不直接连接数据库，只通过 Master HTTP API 上报。
- Web Console 继续优先真实 API，失败时使用 mock fallback。
- P13 仍为下一阶段；本阶段不进入四机部署。
