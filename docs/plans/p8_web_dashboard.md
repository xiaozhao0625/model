# P8：Web Dashboard UI 控制台

## 阶段目标

P8 将 P7 Master Backend 控制平面产品化为可操作、可监控、可交付的 Web 控制台。该阶段定位为 AI 数据采集工业控制中心，不是普通后台管理页。

## 实现范围

- 新增 `apps/web-console/` React + Vite + TypeScript 前端工程。
- 使用 TailwindCSS 建立暗色工业控制台设计系统。
- 实现 Dashboard、Apps Registry、Run Control、Run Detail、Worker Monitor、Upload & Cleanup、Model Gateway、Settings 页面。
- 封装 P7 API client，并在 Master API 不可用时提供 mock fallback，避免 UI 白屏。
- 提供 mock apps、runs、workers、uploads、model providers、summary、run.log、meta.jsonl 展示数据。
- 为 P8 提供前端 smoke test、TypeScript typecheck 和 Vite build 验收。

## 页面

| 页面 | 路径 | 说明 |
| --- | --- | --- |
| Dashboard | `/`、`/dashboard` | 展示 Apps、Runs、Running、Upload Pending、Failed、Workers、有效截图和 bucket 分布。 |
| Apps Registry | `/apps` | 展示 App 列表和创建 App 表单。 |
| Run Control | `/runs` | 展示 Run 列表、状态筛选、App 筛选、创建 Run 和 Start Run 入口。 |
| Run Detail | `/runs/:runId` | 展示 Run 基本信息、状态时间线、bucket 统计、summary.json、run.log、meta.jsonl 和状态门控操作。 |
| Worker Monitor | `/workers` | 展示 Worker 类型、能力、在线状态、心跳和 Web `content_area_only=true` 规则。 |
| Upload & Cleanup | `/upload` | 展示 P2 上传清理状态流、上传队列和清理保护。 |
| Model Gateway | `/model-gateway` | 展示 provider 能力、mock/stub 状态和安全拦截摘要。 |
| Settings | `/settings` | 展示只读环境配置。 |

## 设计系统

- 默认暗色主题：`#0B0F14` 背景、`#111827` surface、`#151C2C` elevated surface。
- 主色：`#3B82F6`；成功、警告、危险分别使用 emerald、amber、red。
- 8px spacing system，卡片圆角 10px，弱边框，高对比文字。
- 左侧导航、中心主内容、右侧日志/状态详情面板。
- UI 保持 operational、data dense、clean，不引入 Ant Design、Material UI 或复杂动画。

## API Client

`apps/web-console/src/lib/api-client.ts` 封装：

- `getHealth`
- `listApps` / `createApp`
- `listRuns` / `createRun` / `getRun` / `startRun` / `getRunSummary`
- `listWorkers` / `registerWorker` / `heartbeatWorker`
- `generateUploadManifest` / `confirmUpload` / `cleanupLocal` / `finalizeRun`
- `sceneClassify` / `ground` / `act`

Upload 操作使用 P7.1 canonical run-scoped routes：

- `POST /api/runs/{run_id}/upload-manifest`
- `POST /api/runs/{run_id}/confirm-upload`
- `POST /api/runs/{run_id}/cleanup`
- `POST /api/runs/{run_id}/finalize`

`VITE_MASTER_API_URL` 控制 API base URL，默认 `http://localhost:8000`。当 API 不可用时，client 返回 mock fallback。

## 边界

- 不修改 P7 数据库结构。
- 不修改后端业务逻辑。
- 不写真实 Worker Runtime。
- 不接真实 OBS、FFmpeg、ADB、Playwright、pywinauto。
- 不接真实模型，不下载模型。
- 不做四机部署。
- 不执行真实鼠标、键盘或系统动作。

## 验收

- `npm install` 成功。
- `npm run lint` 通过。
- `npm run typecheck` 通过。
- `npm run build` 通过。
- `python -m pytest -q` 通过。
- Web Console 可通过 Vite dev server 启动。
