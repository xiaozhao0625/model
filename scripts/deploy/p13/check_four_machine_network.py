from __future__ import annotations

from p13_common import base_parser, check_url, print_json, summarize


def main() -> None:
    parser = base_parser("Check P13 four-machine network reachability.")
    args = parser.parse_args()
    checks = [
        check_url("M0 Master API from current machine", f"{args.master_url.rstrip('/')}/health", args.timeout),
        {"name": "PostgreSQL direct worker access", "status": "skipped", "reason": "workers must not connect DB directly"},
        {"name": "Redis direct worker access", "status": "skipped", "reason": "workers should use Master API boundary"},
    ]
    print_json(
        summarize(
            role="network_check",
            machine_name=args.machine_name or "current",
            checks=checks,
            recommendations=["只开放 Master API 给 W1/W2/W3；数据库和 Redis 不对 Worker 暴露。"],
        )
    )


if __name__ == "__main__":
    main()
