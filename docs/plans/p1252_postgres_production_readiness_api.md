# P12.5.2：PostgreSQL-backed Production Readiness Console API

## 目标

将生产验收控制台的数据源从纯 mock/JSON 临时展示推进到 Master API 持久化能力。默认开发和测试仍使用 SQLite fallback；生产环境可通过 `DATABASE_URL` 切换到 PostgreSQL。

## 边界

- Web Console 优先调用 Master API，API 不可用时保留 mock fallback。
- Worker 不直接连接数据库，只通过 Master HTTP API 上报。
- Master API 是唯一数据库读写入口。
- 不改变 P1-P12.5 核心状态流。
- 不进入 P13 四机部署。
- 不提交 `.env`、真实 `DATABASE_URL`、密码或生产凭据。

## 数据表

生产验收数据表包括：

- `quality_reports`
- `quality_report_items`
- `ocr_reports`
- `ocr_risk_hits`
- `tool_health_snapshots`
- `android_runtime_snapshots`
- `behavior_candidates`
- `behavior_candidate_reviews`
- `behavior_candidate_rollbacks`
- `deployment_diagnostics`

## API

质量报告：

- `GET /api/quality-reports`
- `GET /api/quality-reports/{run_id}`
- `POST /api/quality-reports/ingest`

OCR：

- `GET /api/ocr/status`
- `GET /api/ocr/reports`
- `GET /api/ocr/reports/{run_id}`
- `POST /api/ocr/reports/ingest`

工具健康：

- `GET /api/tool-health`
- `GET /api/tool-health/workers`
- `GET /api/tool-health/android`
- `POST /api/tool-health/ingest`

行为包候选：

- `GET /api/behavior-candidates`
- `GET /api/behavior-candidates/{candidate_pack_id}`
- `POST /api/behavior-candidates/ingest`
- `POST /api/behavior-candidates/{candidate_pack_id}/approve`
- `POST /api/behavior-candidates/{candidate_pack_id}/reject`
- `POST /api/behavior-candidates/{candidate_pack_id}/rollback`

诊断：

- `GET /api/diagnostics`
- `POST /api/diagnostics/ingest`

## PostgreSQL 准备

- 默认测试不要求 PostgreSQL。
- `DATABASE_URL` 支持 `sqlite:///`、`postgresql://`、`postgres://`、`postgresql+psycopg://`。
- PostgreSQL driver 使用 `psycopg[binary]`。
- `scripts/master/smoke_postgres_connection.py` 用于本地连接和 schema smoke；未配置 PostgreSQL 时输出 skipped。
- `.env.example` 只保留占位符，不包含真实凭据。

## 行为包候选审核规则

- 只有 `pending_review` 可 approve/reject。
- approved 后返回 `enabled=true`。
- rejected 不启用。
- rollback 写入 rollback 记录，并将候选恢复到 `pending_review`。
