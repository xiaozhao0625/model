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
| P4 多类型 Worker 与行为包 | in_progress | 已完成 Worker 合同层和行为包 mock 合同层；真实 Worker、真实输入控制和 OBS/FFmpeg 链路仍待后续阶段实现。 |
| P4.1 Worker 合同层 + 能力注册 + Mock Worker | done | 已建立 Worker 合同、能力注册中心和复用 LocalRunSession 的 MockWorker。 |
| P4.2 Behavior Pack 合同层 + FPS/MOBA 示例包 + Mock Runner | done | 已建立行为包合同、JSON 示例包、安全校验和复用 LocalRunSession 的 MockBehaviorRunner。 |
| P5 补采机制与人工补种子 | pending | 等 P2/P4 能力稳定后开始。 |
| P6 行为包自我深化 | pending | 等行为包运行数据稳定后开始。 |
| P7 四机并发与生产化压测 | pending | 等前序能力具备后开始。 |

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
