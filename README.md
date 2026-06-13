# 多类型应用/游戏自动截图采集平台

## 项目目标

本项目是一个独立的新平台仓库，用于建设多类型应用、普通软件、浏览器、Android 应用和 PC 游戏的自动截图采集能力。平台统一管理任务配置、截图分桶、状态流转、本地暂存、上传确认、清理保护、Worker 编排、质量检测、去重、模型网关和审计日志。

app-screenshot-agent 仅作为 Android Worker 和公共质量模块的复用来源，不整体替代新平台架构。

## 核心原则

- 优先开源工具和开源模型。
- 不依赖闭源 Computer Use API 作为核心能力。
- AI 只做低频决策，不做高频逐帧操作。
- PC 游戏 high 桶必须走行为包 + OBS/FFmpeg 抽帧。
- 普通软件和浏览器优先使用 pywinauto、Playwright 等稳定自动化。
- Android 端优先复用 app-screenshot-agent 的 ADB、OCR、去重、质量检测、状态管理能力。
- 本地只暂存，用户确认上传百度网盘后才允许删除本地图片和视频。

## 阶段计划

| 阶段 | 名称 | 状态 |
| --- | --- | --- |
| P0 | 项目基线与开发治理 | done |
| P1 | MVP 基础框架 | done |
| P2 | 本地暂存、上传确认、清理流 | done |
| P3 | 模型网关 | done |
| P4 | 多类型 Worker 与行为包 | done |
| P5 | 补采机制与人工补种子 | done |
| P6 | 环境配置与模型部署预备 | done |
| P7 | Master Backend + PostgreSQL/SQLite + API | done |
| P8 | Web Dashboard UI 控制台 | done |
| P9 | Worker Runtime 与 Master/Worker 通信 | done |
| P10 | 真实采集适配器接入 | done |
| P11 | 模型拉取、模型部署、真实 Provider 接入 | done |
| P12 | 行为包自我深化引擎 | done |
| P12.5-P13Prep | 生产采集就绪强化 | done |
| P12.5.1 | Web Console 生产验收最小入口 | done |
| P13 | 四机部署、分布式调度、并发压测 | next |

## 当前状态

当前已完成 P12.5.1。Web Console 已补齐质量报告、OCR 状态、行为包候选审核、工具健康四个生产验收最小入口。

P12.5.1 不新增依赖，不改核心状态流，不要求真实 OCR/ADB/OBS/FFmpeg/Playwright/pywinauto 存在，不进入 P13。
# P12.5.2 当前状态

P12.5.2 已补齐 PostgreSQL-backed Production Readiness Console API。Master API 现在可以持久化质量报告、OCR 报告、工具健康、Android runtime、行为包候选审核和部署诊断；默认开发/测试仍使用 SQLite fallback，生产环境可通过 `DATABASE_URL` 切换 PostgreSQL。Worker 仍不直连数据库，P13 四机部署尚未开始。

# P13 当前状态

P13 已补齐四机真实部署与验收手册材料，包括 Markdown 源文档、生产 env 示例、启动脚本、健康检查脚本、diagnostics 收集脚本和 DOCX 合并手册。本阶段未下载或安装软件，未操作向日葵，未进入真实四机部署。
