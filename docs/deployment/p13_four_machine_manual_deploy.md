# P13 四机手动部署预备

## 角色

- M0：Master API、Web Console、数据库、Redis、Model Gateway。
- W1：PC Game Worker，后续接 OBS/FFmpeg/行为包。
- W2：PC App/Web Worker，后续接 pywinauto/Playwright/mss/dxcam。
- W3：Android Worker，后续接 ADB/模拟器/OCR fallback。

## 操作原则

本阶段仅提供模板和检查脚本。用户需按本机环境手动安装软件、编辑 env、启动服务。

禁止脚本自动下载、自动安装或自动执行危险动作。
