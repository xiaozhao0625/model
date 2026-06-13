from __future__ import annotations

from p13_common import base_parser, check_python, check_python_module, check_tool, check_url, print_json, summarize


def main() -> None:
    parser = base_parser("Check P13 W2 PC App/Web Worker stack readiness.")
    args = parser.parse_args()
    checks = [
        check_python(),
        check_tool("Git", "git"),
        check_tool("nvidia-smi", "nvidia-smi"),
        check_url("MASTER_URL reachable", f"{args.master_url.rstrip('/')}/health", args.timeout),
        check_python_module("Playwright", "playwright"),
        {"name": "Browser install status", "status": "skipped", "reason": "check with official Playwright command on W2"},
        check_python_module("pywinauto"),
        check_python_module("mss"),
        check_python_module("dxcam"),
        {"name": "Web content-only smoke availability", "status": "skipped", "reason": "run after browser install"},
    ]
    print_json(
        summarize(
            role="pc_app_web_worker",
            machine_name=args.machine_name or "W2",
            checks=checks,
            recommendations=["Web Worker 必须只采集网页内容区，不采集地址栏、标签栏或任务栏。"],
        )
    )


if __name__ == "__main__":
    main()
