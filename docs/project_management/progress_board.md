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
| P3 模型网关 | done | 已完成合同层、service、安全识别、审计、provider 注册中心和 P3 dry-run 总验收；当前不接真实模型。 |
| P3.1 Model Gateway 合同层 + Mock Provider + 安全动作校验 | done | 已建立 scene_classify、ground、act 合同，ActionProposal 和风险动作 safety gate。 |
| P3.2 Gateway Service + 规则风险识别 + 审计日志 | done | 已建立 ModelGatewayService、输入风险规则识别、act 安全封装和 JSONL 审计日志。 |
| P3.2.1 多语言风险词表 + 审计落盘策略 | done | 已抽出可配置中英文风险词表，并固化 audit_log_path/run_dir 审计落盘策略。 |
| P3.3 Provider 适配器骨架 + 注册中心 | done | 已建立 provider 配置、能力声明、注册中心和真实模型 stub provider。 |
| P3.4 Model Gateway dry-run 总验收 | done | 已新增本地 dry-run 脚本，验证 registry、service、风险识别、安全拦截和审计日志串联。 |
| P4 多类型 Worker 与行为包 | done | 已完成 Worker 合同层、行为包 mock 合同层、mock pc_game high 集成、PC Game/PC App/Web/Android adapter stub 骨架和 P4 dry-run 总验收。 |
| P4.1 Worker 合同层 + 能力注册 + Mock Worker | done | 已建立 Worker 合同、能力注册中心和复用 LocalRunSession 的 MockWorker。 |
| P4.2 Behavior Pack 合同层 + FPS/MOBA 示例包 + Mock Runner | done | 已建立行为包合同、JSON 示例包、安全校验和复用 LocalRunSession 的 MockBehaviorRunner。 |
| P4.3 Behavior Pack 接入 Worker，跑通 mock pc_game high 采集 | done | 已建立 BehaviorWorkerAgent，复用 BehaviorPackLoader、BehaviorSafetyGate、MockBehaviorRunner 和 LocalRunSession 跑通 mock high 桶采集。 |
| P4.4 PC Game Worker 适配器骨架：OBS / FFmpeg / Input Adapter 合同 | done | 已建立 OBS Capture、FFmpeg Extract、Game Input adapter 合同、stub 实现和复用 LocalRunSession 的 PcGameStubPipeline。 |
| P4.5 PC App + Web Worker 适配器骨架 | done | 已建立 PC App pywinauto 前置合同、Web Playwright 前置合同、stub adapter 和复用 LocalRunSession 的 low 桶 pipeline。 |
| P4.6 Android Worker 复用入口 | done | 已建立 Android Worker 合同、app-screenshot-agent 复用映射、stub adapter 和复用 LocalRunSession 的 low 桶 pipeline。 |
| P4.7 多类型 Worker 总 dry-run 验收 | done | 已新增 P4 总 dry-run 脚本，验证多类型 Worker 均复用 LocalRunSession 跑通到 capture_completed。 |
| P5 补采机制与人工补种子 | done | 已完成 CoverageManager、RetryPolicy、Manual Seed Gate、failed_low_yield 收口和 P5 dry-run 总验收；不执行真实补采或 Worker 调度。 |
| P5.1 Coverage Manager | done | 已建立 CoverageManager，复用 CompletionGate 判断覆盖是否达标、是否缺少主桶、是否需要继续采集、是否应该停止采集。 |
| P5.2 Retry Policy | done | 已建立 RetryPolicy，复用 CoverageManager 决定继续采集、切换策略、请求人工补种子或标记 failed_low_yield。 |
| P5-Complete 补采机制与人工补种子阶段收口 | done | 已建立人工补种子请求/恢复记录、LocalRunSession 门控、failed_low_yield 收口方法和 P5 双场景 dry-run。 |
| P6 环境配置与模型部署预备 | done | 已完成单机开发拓扑、四机生产拓扑、机器角色、env 模板、模型 manifest、检查脚本和部署文档；不下载模型、不启动服务。 |
| P7 Master Backend + PostgreSQL/SQLite + API | done | 主体已完成并补齐 API 稳定性：FastAPI 可 import、/health、/openapi.json、run-scoped upload canonical routes、兼容 upload routes。 |
| P8 Web Dashboard UI 控制台 | done | 已新增 React + Vite + TypeScript Web Console，包含 Dashboard、Apps、Runs、Run Detail、Workers、Upload、Model Gateway、Settings、API client、mock fallback、暗色工业控制台设计系统、中文化展示和 build 验收。 |
| P8.1 Web Console 中文化 | done | 已将前端可见导航、页面、卡片、表格、按钮、状态说明、上传清理说明、模型网关说明和右侧审计面板中文化；保留 API 字段、路由、枚举、bucket 原始值、worker_type、provider_type 和 capabilities 原始值。 |
| P8.2 Web Console 明暗主题切换 | done | 已新增白天模式 / 夜间模式切换入口，默认夜间模式，使用 localStorage 持久化选择，并通过 CSS variables 保持暗色工业风格与柔和白天模式。 |
| P9 Worker Runtime 与 Master/Worker 通信 | done | 已新增 Worker Agent 配置、Master API client、单轮 runtime、executor resolver、Master claim/report 路由和 P9 dry-run；当前只跑 mock/stub，不接真实采集工具或真实模型。 |
| P10 真实采集适配器接入 | done | 已建立单机 Worker HTTP 进程边界、Web/PC App/PC Game/Android 真实适配器入口、真实工具健康检查、可选 smoke 脚本和 stub fallback；默认测试不依赖真实工具，不进入四机部署。 |
| P12 行为包自我深化引擎 | pending | 迁移早期行为包学习计划到 P12；后续基于历史运行、失败样本、人工补种子和质量反馈优化行为包。 |

## 当前架构基线

- 截图 bucket 只有 fixed、low、high、rejected。
- fixed 可选且最多 10 张。
- low 或 high 至少一种。
- valid_total = fixed + low + high。
- rejected 和 duplicate 不计入 valid_total。
- valid_total >= 1000 且存在 low/high 后才能进入 capture_completed。
- valid_total <= 5000；达到 5000 后停止继续采集，但不新增 completed_max 状态。
- capture_completed 后进入 upload_pending。
- 用户确认已上传百度网盘后，才能进入 uploaded_confirmed。
- uploaded_confirmed 后才允许删除本地图片和临时视频，并进入 local_deleted。
- completed 只能从 local_deleted 进入。
- 删除后必须保留 summary.json、meta.jsonl、upload_manifest.json、upload_record.json、cleanup_record.json、run.log。
- Worker 必须复用 LocalRunSession，不重复实现截图分桶、去重、summary、状态流。
- Worker 不直接进入 completed；上传确认、清理和 completed 收口由 P2 流程负责。
- 行为包是游戏连续操作的核心；P4.2 只实现 JSON 示例包和 MockBehaviorRunner。
- MockBehaviorRunner 必须复用 LocalRunSession，最多推进到 capture_completed，不进入 upload_pending、uploaded_confirmed、local_deleted、completed。
- BehaviorWorkerAgent 必须复用 BehaviorPackLoader、BehaviorSafetyGate、MockBehaviorRunner 和 LocalRunSession。
- mock pc_game high 采集最多推进到 capture_completed，不生成 upload_manifest.json。
- PC Game adapter pipeline 必须复用 LocalRunSession；P4.4 只提供 OBS/FFmpeg/Input stub 合同，不调用真实工具。
- PC App 和 Web pipeline 必须复用 LocalRunSession，默认进入 low 桶。
- Web Worker 后续真实实现必须只采集网页有效内容区，不采集浏览器地址栏、标签栏、Windows 任务栏；P4.5 以 `content_area_only=true` 固化合同。
- Android Worker 必须复用 LocalRunSession，Android 普通 App 默认进入 low 桶。
- app-screenshot-agent 只作为 Android Worker 和公共质量模块的复用来源，不整体替代新平台架构。
- behavior_actions.jsonl 记录行为包 mock 执行审计。
- PC 游戏 high 桶必须使用行为包 + OBS/FFmpeg 抽帧；P4.1 只声明能力，不接真实 OBS/FFmpeg。
- AI 只做低频决策，只能返回 ActionProposal，不直接执行动作。
- 后续业务层不得直接调用 provider，应通过 ModelGatewayService。
- provider 必须声明能力，注册中心按能力选择 provider。
- P3 当前只支持 mock 和 stub provider，不接真实模型。
- 风险判断不能只依赖 provider risk_flags，必须结合可配置中英文风险词表。
- model_gateway.log 必须写入显式 audit_log_path 或 run_dir/model_gateway.log，不默认写当前工作目录。
- 禁止验证码、支付、充值、购买、聊天发送、账号安全验证、反作弊绕过。

## 风险与阻塞

| 风险 | 当前处理 |
| --- | --- |
| P4 真实 Worker 与行为包尚未实现 | P4.1 只建立合同层和 MockWorker，不接真实自动化工具。 |
| PC 游戏 high 桶真实链路复杂 | 继续保留行为包 + OBS/FFmpeg 抽帧架构方向，后续 P4 子阶段再实现。 |
| 后续真实 provider 接入边界不清 | P3 当前只建立合同层、service、mock/stub provider、风险词表和审计；真实模型接入等待架构师指令。 |
| 后续真实上传可能被误解为自动百度网盘 API | P2 只记录 manifest 和用户确认，不接真实百度网盘 API。 |
| 清理流误删本地数据 | 当前只允许删除 fixed、low、high、rejected、temp_video，保留审计文件。 |
