# P3：模型网关

## 目标

建立低频 AI 决策网关，为后续 UI-TARS、ShowUI、Qwen-VL、OmniParser 等开源模型或工具接入预留稳定合同，同时保持高频采集与执行能力由自动化、行为包、OBS/FFmpeg 等模块负责。

## 范围

- Model Gateway 合同层。
- scene_classify、ground、act 三类低频任务。
- ActionProposal 数据结构。
- Mock Provider。
- ModelGatewayService。
- 可配置风险词表。
- 中英文输入风险规则识别。
- Provider 配置、能力声明和注册中心。
- 真实模型适配器 stub provider。
- 高风险动作 safety gate。
- act 调用 JSONL 审计日志。

## 核心规则

- AI 只做低频决策。
- AI 不参与每帧截图。
- AI 不直接执行动作，只能返回 ActionProposal。
- 高频截图和游戏连续动作不走模型。
- 高频游戏采集仍由行为包 + OBS/FFmpeg 负责。
- P3 当前不实现高频游戏采集。
- P3 当前只支持 mock provider 和真实模型 stub provider。
- 后续业务层不得直接调用 provider，应通过 ModelGatewayService。
- provider 必须声明能力，不能让不支持 act 的 provider 处理 act。
- 安全校验仍由 ModelGatewayService + SafetyGate 负责。
- 不新增正式 run 状态。
- 禁止验证码、支付、充值、购买、聊天发送、账号安全验证、反作弊绕过。
- 遇到高风险动作必须 request_manual 或 abort。
- 安全判断不能只依赖 provider 返回的 risk_flags。
- 风险词表必须可配置，并覆盖中文和英文。
- model_gateway.log 不能默认写到当前工作目录。
- model_gateway.log 必须写到显式 audit_log_path 或 run_dir/model_gateway.log。
- 如果提供 run_dir，最终 audit log 路径必须限制在 run_dir 内。
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

## P3.2.1 风险词表与审计落盘

- configs/safety/risk_lexicon.json 保存默认风险词表。
- RiskLexicon 表示风险类型到关键词列表的映射。
- RiskLexiconLoader 负责加载默认或指定词表。
- RiskRuleDetector 使用 RiskLexicon，不再硬编码风险词。
- RiskRuleDetector 必须识别 instruction、target_description、scene_class、context 字符串。
- context 中嵌套 dict/list 的字符串也必须参与识别。
- ModelGatewayService 允许显式 audit_log_path。
- ModelGatewayService 允许 run_dir，并默认写入 run_dir/model_gateway.log。
- 如果提供 run_dir，audit_log_path 必须位于 run_dir 内，禁止路径逃逸。
- 不指定 audit_log_path 或 run_dir 时，act 调用必须失败并给出明确错误。

## P3.3 Provider 注册中心

- ProviderType 固定包含 mock、ui_tars、showui、qwen_vl、omniparser、gui_actor、os_atlas。
- ProviderCapabilities 声明 supports_scene_classify、supports_ground、supports_act、requires_gpu、default_device。
- ProviderConfig 声明 provider_name、provider_type、enabled、capabilities、config。
- ProviderConfigLoader 从 JSON 加载 provider 配置。
- configs/model_gateway/providers.example.json 提供 mock、ui_tars、showui、qwen_vl、omniparser 示例配置。
- ProviderRegistry 支持 register、get、list_enabled、select_for_task。
- select_for_task 必须按 enabled 和 capability 过滤。
- 不支持 act 的 provider 不能被 select_for_task(act) 选中。
- stub provider 不调用真实模型，不导入 torch/transformers。

## Stub Provider 行为

- Mock 复用 MockModelGatewayProvider。
- UI-TARS stub 不调用真实模型，只返回 request_manual 或 no_op。
- ShowUI stub 不调用真实模型，ground 返回 found=false；act 不支持。
- Qwen-VL stub 不调用真实模型，scene_classify 返回 unknown。
- OmniParser stub 不调用真实模型，ground 返回 found=false；act 不支持。
- 所有 stub provider 必须明确 provider_name。

## 风险词表结构

默认风险类型：

- captcha
- payment
- recharge
- purchase
- send_chat
- account_security
- anti_cheat_bypass

每个风险类型映射到一个非空关键词列表，关键词必须包含中文和英文表达。

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
- 不引入 torch。
- 不引入 transformers。
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

- providers.example.json 可以加载。
- ProviderConfig 字段解析正确。
- ProviderRegistry 可以注册 mock 和真实模型 stub provider。
- disabled provider 不出现在 list_enabled。
- select_for_task 按 scene_classify、ground、act capability 过滤。
- 不支持 act 的 provider 处理 act 时失败或不可被选中。
- 未知 provider type 报错。
- stub provider 不执行真实动作。
- stub provider 不导入 torch/transformers。
- GatewayService 可以使用 registry 返回的 mock provider 完成安全 act。
- 完整单元测试通过。
