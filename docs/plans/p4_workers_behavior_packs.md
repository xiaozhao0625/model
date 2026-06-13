# P4: 多类型 Worker 与行为包

## 目标

建立 Web、PC 普通软件、Android、PC 游戏等多类型 Worker 的统一合同层，并在后续阶段引入行为包机制处理可重复动作序列。

P4 仍遵守既有架构基线：Worker 复用 `LocalRunSession`，不重复实现截图分桶、去重、summary、状态流；上传确认、清理和 completed 收口仍归 P2 流程处理。

## P4.1 Worker 合同层 + 能力注册 + Mock Worker

状态：done。

已完成内容：

- 定义 `WorkerType`：`mock`、`pc_game`、`pc_app`、`web`、`android`。
- 定义 `WorkerCapability`：`capture_low`、`capture_high`、`manual_gate`、`model_gateway`、`behavior_pack`、`obs_capture`、`ffmpeg_extract`、`adb`、`playwright`、`pywinauto`、`upload_flow`。
- 定义 `WorkerState`：`idle`、`assigned`、`running`、`stopped`、`failed`。
- 定义 `WorkerProfile`、`WorkerTask`、`WorkerResult`。
- 实现 `WorkerRegistry`，支持注册、获取、列出可用 Worker、按能力筛选 Worker。
- 实现 `MockWorkerAgent`，通过 `LocalRunSession` 完成 mock 图片采集并最多推进到 `capture_completed`。

P4.1 明确未实现：

- 不接真实 OBS。
- 不接真实 FFmpeg。
- 不接真实 ADB。
- 不接真实 Playwright。
- 不接真实 pywinauto。
- 不接 Airtest/Appium。
- 不执行真实鼠标、键盘或系统动作。
- 不生成 `upload_manifest.json`。
- 不进入 `upload_pending`、`uploaded_confirmed`、`local_deleted`、`completed`。

## P4.2 Behavior Pack 合同层 + FPS/MOBA 示例包 + Mock Runner

状态：done。

已完成内容：

- 定义 `GameType`：`fps`、`moba`、`open_world`、`2d_game`、`mobile_game`。
- 定义 `BehaviorActionType`：`move`、`camera`、`combat`、`ui`、`recovery`、`wait`、`capture_hint`、`request_manual`、`abort`。
- 定义 `BehaviorAction`、`BehaviorPack`、`BehaviorSafetyDecision`、`BehaviorRunResult`。
- 实现 `BehaviorPackLoader`，从 JSON 示例包加载并校验必填字段。
- 实现 `BehaviorSafetyGate`，检查 `forbidden_context` 和动作 `risk_flags`。
- 新增 `fps_mock_v1.example.json`，声明 FPS high 桶、`record_then_extract=true`、move/camera/combat/recovery/capture_hint 示例动作。
- 新增 `moba_mock_v1.example.json`，声明 MOBA high 桶、`record_then_extract=true`、move/camera/combat/ui/recovery/capture_hint 示例动作。
- 实现 `MockBehaviorRunner`，复用 `LocalRunSession`，写入 `behavior_actions.jsonl`，生成 mock 图片，并最多推进到 `capture_completed`。

P4.2 明确未实现：

- 不接真实 AutoHotkey。
- 不接真实 pydirectinput。
- 不接真实 OBS。
- 不接真实 FFmpeg。
- 不接真实 ADB。
- 不接 Airtest/Appium。
- 不接真实 Playwright。
- 不接真实 pywinauto。
- 不执行真实鼠标或键盘动作。
- 不生成 `upload_manifest.json`。
- 不进入 `upload_pending`、`uploaded_confirmed`、`local_deleted`、`completed`。

## P4.3 Behavior Pack 接入 Worker，跑通 mock pc_game high 采集

状态：done。

已完成内容：

- 扩展 `WorkerTask`，增加可选 `behavior_pack_path`、`behavior_pack_id`、`context`。
- 扩展 `WorkerResult`，增加可选 `behavior_pack_id`、`behavior_actions_path`。
- 新增 `BehaviorWorkerAgent`，用于模拟 PC Game Worker 通过行为包生成 high 桶截图。
- `BehaviorWorkerAgent` 复用 `BehaviorPackLoader`、`BehaviorSafetyGate`、`MockBehaviorRunner` 和 `LocalRunSession`。
- 成功执行后生成 `summary.json`、`meta.jsonl`、`run.log`、`behavior_actions.jsonl`。
- target_min 较小时可推进到 `capture_completed`。
- forbidden_context 或高风险 action 命中时返回 `WorkerResult.error`，不生成有效截图，不进入 `capture_completed`。

P4.3 明确未实现：

- 不接真实 OBS。
- 不接真实 FFmpeg。
- 不接真实 AutoHotkey。
- 不接真实 pydirectinput。
- 不接真实 ADB。
- 不接 Airtest/Appium。
- 不接真实 Playwright。
- 不接真实 pywinauto。
- 不执行真实鼠标或键盘动作。
- 不生成 `upload_manifest.json`。
- 不进入 `upload_pending`、`uploaded_confirmed`、`local_deleted`、`completed`。

## Worker 策略

- Web Worker 后续优先使用 Playwright，但 P4.1 只声明能力，不接真实 Playwright。
- PC App Worker 后续优先使用 pywinauto，但 P4.1 只声明能力，不接真实 pywinauto。
- Android Worker 后续优先复用 app-screenshot-agent 的 ADB、OCR、去重、质量检测、状态管理能力，但 P4.1 只声明能力，不接真实 ADB。
- PC 游戏 high 桶后续必须使用行为包 + OBS/FFmpeg 抽帧；P4.1 只声明 `behavior_pack`、`obs_capture`、`ffmpeg_extract` 能力，P4.2 只建立行为包合同和 mock runner，P4.3 只跑通 mock pc_game high 集成，不实现真实链路。

## 行为包原则

- 行为包负责高频、重复、可审计动作。
- AI 只参与启动、场景判断、按钮定位、卡住恢复等低频决策。
- AI 不参与 Worker 高频逐帧执行。
- 高频游戏采集不走模型逐帧控制。
- `forbidden_context` 命中或动作 `risk_flags` 包含禁止风险时，行为包 runner 必须 `request_manual` 或 `abort`。
- P4.2 使用 JSON 示例包，不引入 YAML 依赖。

## 禁止范围

- 不自动处理验证码、支付、充值、购买、聊天发送、账号安全验证、反作弊绕过。
- 不让模型逐帧控制游戏。
- 不绕过平台统一状态机。
- 不在 Worker 中直接进入 completed。
- 不在行为包 mock runner 中执行真实系统动作。

## 验收标准

- 每类 Worker 有清晰能力边界。
- PC 游戏 high 桶链路必须保留行为包 + OBS/FFmpeg 抽帧方向。
- Worker 输出服从统一 bucket 规则和 valid_total 规则。
- Mock Worker 可用于本地单元测试和后续 P4 dry-run 验证。
- Mock Behavior Runner 可用于本地单元测试和后续 FPS/MOBA 行为包 dry-run 验证。
