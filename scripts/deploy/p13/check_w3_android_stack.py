from __future__ import annotations

from p13_common import base_parser, check_python, check_tool, check_url, print_json, summarize


def main() -> None:
    parser = base_parser("Check P13 W3 Android Worker stack readiness.")
    args = parser.parse_args()
    checks = [
        check_python(),
        check_tool("Git", "git"),
        check_tool("nvidia-smi", "nvidia-smi"),
        check_url("MASTER_URL reachable", f"{args.master_url.rstrip('/')}/health", args.timeout),
        check_tool("ADB", "adb"),
        {"name": "adb devices", "status": "skipped", "reason": "run manually on W3 when device/emulator is ready"},
        {"name": "Android emulator", "status": "skipped", "reason": "manual emulator profile check required"},
        {"name": "screencap availability", "status": "skipped", "reason": "run after adb device is online"},
        {"name": "uiautomator dump availability", "status": "skipped", "reason": "run after adb device is online"},
        {"name": "Android Worker dry-run", "status": "skipped", "reason": "run after device profile is selected"},
    ]
    print_json(
        summarize(
            role="android_worker",
            machine_name=args.machine_name or "W3",
            checks=checks,
            recommendations=["ADB/OCR/模拟器真实依赖保持 optional；不可用时记录 skipped/unavailable。"],
        )
    )


if __name__ == "__main__":
    main()
