# P3：模型网关

## 目标

建立低频 AI 决策网关，为后续 UI-TARS、ShowUI、Qwen-VL、OmniParser 等开源模型或工具接入预留稳定合同，同时保持高频采集与执行能力由自动化、行为包、OBS/FFmpeg 等模块负责。

## 范围

- Model Gateway 合同层。
- scene_classify、ground、act 三类低频任务。
- ActionProposal 数据结构。
- Mock Provider。
- ModelGatewayService。
- 输入风险规则识别。
- 高风险动作 safety gate。
- act 调用 JSONL 审计日志。
- 后续模型接入的 provider 边界。

## 核心规则

- AI 只做低频决策。
- AI 不参与每帧截图。
- AI 不直接执行动作，只能返回 ActionProposal。
- 高频截图和游戏连续动作不走模型。
- 高频游戏采集仍由行为包 + OBS/FFmpeg 负责。
- P3 当前不实现高频游戏采集。
- P3 当前只支持 mock provider。
- 后续业务层不得直接调用 provider，应通过 ModelGatewayService。
- 不新增正式 run 状态。
- 禁止验证码、支付、充值、购买、聊天发送、账号安全验证、反作弊绕过。
- 遇到高风险动作必须 request_manual 或 abort。
- 安全判断不能只依赖 provider 返回的 risk_flags。
- 不依赖闭源 Computer Use API 作为核心能力。

## P3.1 合同层

- ModelTaskType 固定包含 scene_classify、ground、act。
- SceneClass 覆盖 launcher、login、menu、document、browser_page、open_world、combat、shop、scoreboard、death、result_screen、unknown。
- SceneClassifyRequest 和 SceneClassifyResult 只表达场景分类请求和结果。
- GroundRequest 和 GroundResult 只表达目标定位请求和结果。
- ActRequest 和 ActionProposal 只表达低频动作建议。
- ActionType 只允许 click、key_press、wait、no_op、request_manual、abort。
- ModelGatewayProvider 是抽象合同，不绑定真实模型。
- MockModelGatewayProvider 可根据 context 返回可控 scene_class、坐标和 action proposal。
- ModelActionSafetyGate 检查 risk_flags，命中禁止风险后返回 request_manual 或 abort。

## P3.2 Gateway Service

- ModelGatewayService 包装已有 ModelGatewayProvider。
- scene_classify 和 ground 直接走 provider，并保留 provider_name。
- act 必须执行输入风险检测。
- act 必须合并输入风险和 provider risk_flags。
- act 必须调用 ModelActionSafetyGate 做安全后处理。
- 输入风险已命中高危时，可以不调用 provider，直接返回 request_manual。
- 所有 act 调用必须写 model_gateway.log。
- 审计日志为 JSONL。
- service 不执行任何鼠标、键盘、ADB 或系统命令。

## 风险识别规则

RiskRuleDetector 从 instruction、target_description、context、scene_class 等输入文本中识别风险意图。

禁止风险类型：

- captcha
- payment
- recharge
- purchase
- send_chat
- account_security
- anti_cheat_bypass

命中上述任意风险时，service 或 safety gate 必须拒绝原动作，并返回 request_manual 或 abort。

## 审计日志字段

model_gateway.log 每行至少包含：

- timestamp
- app_id
- run_id
- task_type
- provider_name
- input_risk_flags
- output_risk_flags
- final_action_type
- blocked
- reason

## 不做

- 不接真实模型。
- 不下载模型。
- 不实现 FastAPI。
- 不实现 UI。
- 不接数据库。
- 不实现 Worker。
- 不接 OBS。
- 不接 ADB。
- 不接 OCR。
- 不执行鼠标、键盘、ADB 或系统命令。
- 不实现 PC 游戏 high 桶的行为包 + OBS/FFmpeg 采集。

## 验收标准

- service 可以调用 scene_classify。
- service 可以调用 ground。
- service 可以调用安全 act。
- instruction 中包含 captcha、payment、purchase、send_chat 时被拦截。
- context 中包含 anti_cheat_bypass 时被拦截。
- provider 返回危险 risk_flags 时被拦截。
- 被拦截动作返回 request_manual 或 abort。
- 安全 act 不被误拦截。
- act 调用写入 model_gateway.log。
- 审计日志是合法 JSONL。
- 完整单元测试通过。
