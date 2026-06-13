# M0 Master 部署步骤

## 目标

M0 承载 Master API、PostgreSQL、Redis、Web Console、Model Gateway 和生产验收 API。M0 是唯一数据库读写入口，Worker 不直连数据库。

## 手动准备

1. 安装 Python、Git、Node.js、PostgreSQL、Redis。
2. 克隆项目仓库到固定目录，例如 `D:\projects\ai-screenshot-platform`。
3. 创建 Python 虚拟环境并安装项目依赖。
4. 在 PostgreSQL 中创建数据库和用户。
5. 复制 `configs/deploy/m0_master.production.env.example` 为本机 `.env`，填写占位符。

## PostgreSQL 配置

`.env` 中只能在本机填写真实密码，不要提交：

```text
DATABASE_URL=postgresql+psycopg://screenshot_app:<password>@127.0.0.1:5432/ai_screenshot_platform
PSQL_PATH=D:\work\pgsql\bin\psql.exe
```

## 启动顺序

1. 启动 PostgreSQL。
2. 启动 Redis。
3. 运行 `python scripts/master/smoke_postgres_connection.py`。
4. 启动 Master API。
5. 启动 Web Console。
6. 打开 Web Console，确认 API fallback 未启用。

## 健康检查

```powershell
python scripts/deploy/p13/check_m0_master_stack.py
```

输出应为 JSON，重点查看：

- `PostgreSQL`
- `DATABASE_URL`
- `Master API health`
- `Web Console`
- `Model Gateway mode`

## 验收

- `/health` 返回成功。
- `/openapi.json` 可访问。
- production readiness API 可写入 PostgreSQL。
- Web Console 显示真实 API 数据，不只是 mock fallback。
