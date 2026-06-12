# 项目进度看板

## 当前阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| P0 项目基线与开发治理 | done | 已建立项目文档、阶段计划、Codex 工作协议和架构基线。 |
| P0.1 Git 基线与 P0 文档入库 | done | 已初始化独立项目仓库，P0 文档已入库。 |
| P0.2 状态流规范化 + 换行规则固化 | done | 已固化正式状态流和 Git 换行规则。 |
| P1 MVP 基础框架 | done | 已完成核心领域模型、完成判定 Gate、本地分桶存储、content_hash 去重、meta 恢复、生命周期状态机、LocalRunSession、run.log 和 P1 dry-run。 |
| P1.1 核心领域模型 + 完成判定 Gate | done | 已代码化截图分桶、有效总数和完成判定规则。 |
| P1.2 BucketedScreenshotStore + meta.jsonl + summary.json | done | 已实现本地分桶目录、图片落盘、meta.jsonl 和 summary.json。 |
| P1.3 基础去重索引 + content_hash 去重 | done | 已实现 run 内 sha256 content_hash 精确去重。 |
| P1.4 Store 恢复能力 + dedup 从 meta.jsonl 重建 | done | 已支持从 meta.jsonl 恢复计数、编号和 content_hash 去重索引。 |
| P1.5 Run 生命周期状态机 | done | 已实现 run 状态流转约束和终止态保护。 |
| P1.5.1 RunStatus 命名统一 | done | 已移除 CREATED 和 CAPTURE_RUNNING 历史状态。 |
| P1.6 LocalRunSession + run.log 集成层 | done | 已串联生命周期、存储、完成判定和 JSONL run.log。 |
| P1.7 本地 dry-run 验收脚本 + P1 收口 | done | 已新增 mock dry-run 脚本并完成 P1 验收收口。 |
| P2 本地暂存、上传确认、清理流 | done | 已完成 upload_manifest、人工上传确认、local_deleted 安全清理、completed 收口、状态恢复和 P2 dry-run 总验收。 |
| P2.1 upload_manifest.json 生成 | done | 已支持 capture_completed 后生成 upload_manifest.json 并进入 upload_pending。 |
| P2.2 上传确认记录 + uploaded_confirmed 状态推进 | done | 已支持用户确认后生成 upload_record.json 并进入 uploaded_confirmed。 |
| P2.3 本地安全清理 local_deleted | done | 已支持 uploaded_confirmed 后仅清理本地大文件目录并进入 local_deleted。 |
| P2.4 completed 收口 + P2 dry-run 总验收 | done | 已支持 local_deleted -> completed，并新增 P2 全流程 dry-run 脚本。 |
| P2.5 本地状态恢复与 P2 收口 | done | 已支持根据本地轻量记录文件恢复 run 当前状态。 |
| P3 模型网关 | in_progress | 已进入 mock-only 网关阶段；当前不接真实模型。 |
| P3.1 Model Gateway 合同层 + Mock Provider + 安全动作校验 | done | 已建立 scene_classify、ground、act 合同，ActionProposal 和风险动作 safety gate。 |
| P3.2 Gateway Service + 规则风险识别 + 审计日志 | done | 已建立 ModelGatewayService、输入风险规则识别、act 安全封装和 JSONL 审计日志。 |
| P4 多类型 Worker 与行为包 | pending | 等 P3/P4 阶段指令后开始。 |
| P5 补采机制与人工补种子 | pending | 等 P2/P4 能力稳定后开始。 |
| P6 行为包自我深化 | pending | 等行为包运行数据稳定后开始。 |
| P7 四机并发与生产化压测 | pending | 等前序能力具备后开始。 |

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

## 当前架构基线

- 截图 bucket 只有 fixed、low、high、rejected。
- fixed 可选且最多 10 张。
- low 或 high 至少一种。
- valid_total = fixed + low + high。
- valid_total >= 1000 且存在 low/high 后才能进入 capture_completed。
- valid_total <= 5000；达到 5000 后停止继续采集，但不新增 completed_max 状态。
- capture_completed 后进入 upload_pending。
- 用户确认已上传百度网盘后，才能进入 uploaded_confirmed。
- uploaded_confirmed 后才允许删除本地图片和临时视频，并进入 local_deleted。
- completed 只能从 local_deleted 进入。
- 删除后必须保留 summary.json、meta.jsonl、upload_manifest.json、upload_record.json、cleanup_record.json、run.log。
- 本地状态恢复只读取已有轻量记录文件，不生成上传或清理记录，不删除任何文件。
- AI 只做低频决策，只能返回 ActionProposal，不直接执行动作。
- 后续业务层不得直接调用 provider，应通过 ModelGatewayService。
- P3 当前只支持 mock provider，不接真实模型。
- 禁止验证码、支付、充值、购买、聊天发送、账号安全验证、反作弊绕过。

## 风险与阻塞

| 风险 | 当前处理 |
| --- | --- |
| P3 后续真实 provider 接入边界不清 | P3.1/P3.2 只建立合同层、service、mock provider 和审计，真实模型接入等待架构师指令。 |
| 后续真实上传可能被误解为自动百度网盘 API | P2 只记录 manifest 和用户确认，不接真实百度网盘 API。 |
| 清理流误删本地数据 | 当前只允许删除 fixed、low、high、rejected、temp_video，保留审计文件。 |
| 状态恢复与真实任务调度边界尚未接入 | P2.5 只提供本地 resolver 和会话恢复入口，不实现 Worker 或数据库。 |
