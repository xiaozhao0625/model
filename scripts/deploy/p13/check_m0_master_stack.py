from __future__ import annotations

from pathlib import Path

from p13_common import (
    REPO_ROOT,
    base_parser,
    check_env_present,
    check_port,
    check_python,
    check_tool,
    check_url,
    file_check,
    print_json,
    summarize,
)


def main() -> None:
    parser = base_parser("Check P13 M0 Master stack readiness.")
    parser.add_argument("--web-url", default="http://127.0.0.1:5173")
    args = parser.parse_args()
    checks = [
        check_python(),
        check_tool("Git", "git"),
        check_tool("nvidia-smi", "nvidia-smi"),
        check_tool("PostgreSQL psql", "psql"),
        check_env_present("DATABASE_URL"),
        file_check("smoke_postgres_connection.py", REPO_ROOT / "scripts/master/smoke_postgres_connection.py"),
        check_port("127.0.0.1", 6379, args.timeout),
        check_url("Master API health", f"{args.master_url.rstrip('/')}/health", args.timeout),
        check_url("Web Console", args.web_url, args.timeout),
        {"name": "Model Gateway mode", "status": "available", "mode": "mock_or_configured"},
    ]
    print_json(
        summarize(
            role="master",
            machine_name=args.machine_name or "M0",
            checks=checks,
            recommendations=[
                "不要在日志中打印完整 DATABASE_URL。",
                "Worker 只能访问 Master API，不要配置数据库连接串。",
            ],
        )
    )


if __name__ == "__main__":
    main()
