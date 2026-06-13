# P13：四机真实部署与验收总览

## 阶段目标

P13 用于指导用户通过向日葵等远程工具，在四台 Windows 机器上手动完成真实部署、健康检查和小规模 smoke 验收。本阶段只交付部署材料、配置模板、启动脚本、健康检查脚本、diagnostics 收集方案和 DOCX 手册。

Codex 不下载软件、不安装软件、不操作向日葵、不进入真实四机部署、不提交 `.env`、不提交安装包或二进制文件。

## 四机角色

| 机器 | 角色 | 主要组件 |
| --- | --- | --- |
| M0 / 5060Ti | Master | Master API、PostgreSQL、Redis、Web Console、Model Gateway、生产验收 API |
| W1 / 3060 | PC Game Worker | PC Game Worker、OBS、FFmpeg、行为包、high 桶采集 |
| W2 / 3060 | PC App / Web Worker | Playwright、pywinauto、mss、dxcam、low 桶采集 |
| W3 / 3060 | Android Worker | Android SDK Platform-Tools、ADB、Android Emulator、Android App/手游采集 |

## P13 做什么

1. 明确每台机器需要安装的软件。
2. 明确每台机器 `.env` 应如何填写。
3. 明确 M0、W1、W2、W3 的启动顺序。
4. 提供每台机器可运行的健康检查脚本。
5. 提供真实 smoke test 流程。
6. 说明 smoke 结果如何写入 PostgreSQL。
7. 说明 Web Console 如何确认真实 API 数据而不是 mock fallback。
8. 提供 diagnostics 收集脚本和故障排查表。

## P13 不做什么

- 不下载或安装软件。
- 不下载大模型，不训练模型。
- 不做大规模生产采集，只做小规模真实 smoke。
- 不绕过验证码、支付、充值、购买、账号安全、聊天发送或反作弊。
- 不允许 Worker 直连数据库，Worker 只能通过 Master HTTP API 上报。
- 不移除 SQLite fallback，不移除 Web Console mock fallback。

## 验收原则

P13 通过的标志不是“所有真实工具都必须可用”，而是：

- 可用工具能被识别并完成小规模 smoke。
- 不可用工具有明确 `unavailable` / `skipped` 原因。
- 生产验收数据能通过 Master API 写入 PostgreSQL。
- Web Console 能显示真实 API 数据。
- diagnostics 能收集足够信息供架构师排查。
