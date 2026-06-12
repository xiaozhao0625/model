# P3：模型网关

## 目标

建立低频 AI 决策网关，为后续 UI-TARS、ShowUI、Qwen-VL、OmniParser 等开源模型或工具接入预留稳定合同，同时保持高频采集与执行能力由自动化、行为包、OBS/FFmpeg 等模块负责。

## 范围

- Model Gateway 合同层。
- scene_classify、ground、act 三类低频任务。
- ActionProposal 数据结构。
- Mock Provider。
- 高风险动作 safety gate。
- 后续模型接入的 provider 边界。

## 核心规则

- AI 只做低频决策。
- AI 不参与每帧截图。
- AI 不直接执行动作，只能返回 ActionProposal。
- 高频游戏采集仍由行为包 + OBS/FFmpeg 负责。
- P3.1 不实现高频游戏采集。
- P3.1 只支持 mock provider。
- 不新增正式 run 状态。
- 禁止验证码、支付、充值、购买、聊天发送、账号安全验证、反作弊绕过。
- 遇到高风险动作必须 request_manual 或 abort。
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

## 安全动作校验

禁止风险标记：

- captcha
- payment
- recharge
- purchase
- send_chat
- account_security
- anti_cheat_bypass

命中上述任意 risk_flags 时，safety gate 必须拒绝原动作，并返回 request_manual 或 abort。

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

- Mock Provider 可以返回 scene_classify 结果。
- Mock Provider 可以返回 ground 结果。
- Mock Provider 可以返回 act 结果。
- ActionProposal 不执行真实动作。
- 安全动作通过 safety gate。
- captcha、payment、purchase、send_chat、anti_cheat_bypass 风险会被拒绝。
- 被拒绝动作返回 request_manual 或 abort。
- 完整单元测试通过。
