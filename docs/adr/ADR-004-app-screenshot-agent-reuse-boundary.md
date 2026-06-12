# ADR-004：app-screenshot-agent 复用边界

## 状态

Accepted

## 背景

app-screenshot-agent 已具备 Android 截图采集、ADB、OCR、去重、质量检测和状态管理能力。新平台需要复用这些能力，但平台目标覆盖多类型应用和 PC 游戏，不能直接被 Android 单端架构替代。

## 决策

- app-screenshot-agent 只作为 Android Worker 和公共质量模块的复用基础。
- 不整体替代新平台架构。
- 不绕过本平台桶规则、valid_total、状态机、上传确认和删除保护。
- 不把 Android 实现方式强行套用到浏览器、普通软件或 PC 游戏 Worker。

## 影响

- P4 Android Worker 可以封装其可复用模块。
- P1/P2/P3 的平台核心能力必须独立定义。
- 公共质量模块复用时必须服从平台统一审计。

