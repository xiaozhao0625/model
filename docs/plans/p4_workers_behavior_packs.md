# P4：多类型 Worker 与行为包

## 目标

建立浏览器、普通软件、Android、PC 游戏 Worker，并引入行为包机制处理可重复动作序列。

## Worker 策略

- 浏览器优先使用 Playwright。
- 普通软件优先使用 pywinauto。
- Android 优先复用 app-screenshot-agent 的 ADB、OCR、去重、质量检测、状态管理能力。
- PC 游戏 high 桶必须使用行为包 + OBS/FFmpeg 抽帧。

## 行为包原则

- 行为包负责高频、重复、可审计动作。
- AI 只参与行为包启动、场景判断、按钮定位、卡住恢复等低频决策。
- 行为包必须记录执行结果和失败原因。

## 不做

- 不自动处理验证码、支付、充值、购买、聊天发送、账号安全验证、反作弊绕过。
- 不让模型逐帧控制游戏。
- 不绕过平台统一状态机。

## 验收标准

- 每类 Worker 有清晰边界。
- PC 游戏 high 桶采集链路包含行为包和 OBS/FFmpeg 抽帧。
- Worker 输出服从统一桶规则和 valid_total 规则。

