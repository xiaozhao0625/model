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
| P8 | Web Dashboard UI 控制台 | done |
| P9 | Worker Runtime 与 Master/Worker 通信 | done |
| P10 | 真实采集适配器接入 | done |
| P11 | 模型拉取、模型部署、真实 Provider 接入 | done |
| P12 | 行为包自我深化引擎 | pending |
| P13 | 四机部署、分布式调度、并发压测 | pending |

## 当前状态

当前项目已完成 P11：模型拉取、模型部署、真实 Provider 接入。P8 Web Dashboard UI 控制台已完成，并完成 P8.1 中文化补丁和 P8.2 明暗主题切换补丁。

P8 将 P7 后端控制平面产品化为可操作、可监控、可交付的中文 Web 控制台，并支持白天模式 / 夜间模式切换；仍不写真实 Worker 执行逻辑，不做真实截图/行为包/真实模型推理，不做四机实机部署。
P9 建立单机 Master/Worker mock 闭环：Worker 注册、心跳、领取任务、复用 P4 mock/stub pipeline 执行、上报结果，并由 Master 更新 run 到 capture_completed；仍不接真实采集工具、不接真实模型、不做四机部署。
P10 开始定义真实采集适配器入口和 Worker HTTP 进程边界，新增 Web/PC App/PC Game/Android 可选真实工具健康检查与 smoke 脚本；默认仍使用 stub/fallback，不强制安装真实工具，不进入四机部署。
P11 建立模型 manifest、模型文件健康检查、下载计划、Provider runtime、真实 Provider 边界和 mock fallback；默认不下载模型、不要求 GPU、不引入 torch/transformers 默认依赖。

## app-screenshot-agent 复用边界

app-screenshot-agent 仅作为 Android Worker 和公共质量模块的复用来源。新平台不直接在 app-screenshot-agent 旧仓库中开发，也不让 app-screenshot-agent 整体替代新平台架构。
