# 多类型应用/游戏自动截图采集平台

## 项目目标

本项目是一个独立的新平台仓库，用于建设多类型应用、普通软件、浏览器、Android 应用和 PC 游戏的自动截图采集能力。平台统一管理任务配置、截图桶规则、状态流转、本地暂存、上传确认、清理保护、Worker 编排、质量检测、去重和审计日志。

核心原则：

- 优先开源工具和开源模型。
- 不依赖闭源 Computer Use API 作为核心能力。
- AI 只做低频决策，不做高频逐帧操作。
- PC 游戏 high 桶必须走行为包 + OBS/FFmpeg 抽帧。
- 普通软件和浏览器优先使用 pywinauto、Playwright 等稳定自动化。
- Android 端优先复用 app-screenshot-agent 的 ADB、OCR、去重、质量检测、状态管理能力。

## 阶段计划

| 阶段 | 名称 | 状态 |
| --- | --- | --- |
| P0 | 项目基线与开发治理 | completed |
| P0.1 | Git 基线与 P0 文档入库 | current |
| P1 | MVP 基础框架 | pending |
| P2 | 本地暂存、上传确认、清理流 | pending |
| P3 | 模型网关 | pending |
| P4 | 多类型 Worker 与行为包 | pending |
| P5 | 补采机制与人工补种子 | pending |
| P6 | 环境配置与模型部署预备 | done |
| P7 | Master Backend + PostgreSQL/SQLite + API | done |
| P8 | Web Dashboard UI 控制台 | next |
| P12 | 行为包自我深化引擎 | pending |
| P13 | 四机实机部署与生产化压测 | pending |

## 当前状态

当前项目已完成 P7：Master Backend + PostgreSQL/SQLite + API。

P7 建立后端控制平面，不写 Worker 执行逻辑，不做截图/行为包/真实模型推理，不做 UI，不做四机实机部署。

## app-screenshot-agent 复用边界

app-screenshot-agent 仅作为 Android Worker 和公共质量模块的复用来源。新平台不直接在 app-screenshot-agent 旧仓库中开发，也不让 app-screenshot-agent 整体替代新平台架构。
