# 项目进度看板

## 当前阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| P0 项目基线与开发治理 | in_progress | 建立文档、阶段计划、Codex 工作协议和架构基线 |
| P1 MVP 基础框架 | pending | 等 P0 完成并确认后开始 |
| P2 本地暂存、上传确认、清理流 | pending | 等 P1 基础框架完成后开始 |
| P3 模型网关 | pending | 等 P1 基础框架完成后开始 |
| P4 多类型 Worker 与行为包 | pending | 等 P1/P3 基础能力明确后开始 |
| P5 补采机制与人工补种子 | pending | 等 P2/P4 完成后开始 |
| P6 行为包自我深化 | pending | 等行为包运行数据稳定后开始 |
| P7 四机并发与生产化压测 | pending | 等前序能力具备后开始 |

## P0 任务清单

| 任务 | 状态 | 验收 |
| --- | --- | --- |
| 阶段计划 | done | docs/project_management/phase_plan.md |
| 进度看板 | done | docs/project_management/progress_board.md |
| Codex 工作协议 | done | docs/project_management/codex_work_protocol.md |
| 架构实现基线 | done | docs/architecture/implementation_baseline.md |
| app-screenshot-agent 复用边界 | done | docs/integration/app_screenshot_agent_reuse.md |
| P1-P7 分阶段计划 | done | docs/plans/*.md |
| ADR-001 到 ADR-005 | done | docs/adr/*.md |

## 风险与阻塞

| 风险 | 当前处理 |
| --- | --- |
| 当前目录可能未初始化 Git 仓库 | 命令结果如实记录；不影响文档创建 |
| 后续阶段可能引入模型或自动化依赖 | 必须由阶段计划和架构师确认后再引入 |
| 清理流误删本地数据 | P2 必须实现 uploaded_confirmed 前删除保护 |

