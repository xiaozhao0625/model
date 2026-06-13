from __future__ import annotations

from p13_common import base_parser, check_python, check_tool, check_url, print_json, summarize


def main() -> None:
    parser = base_parser("Check P13 W1 PC Game Worker stack readiness.")
    args = parser.parse_args()
    checks = [
        check_python(),
        check_tool("Git", "git"),
        check_tool("nvidia-smi", "nvidia-smi"),
        check_url("MASTER_URL reachable", f"{args.master_url.rstrip('/')}/health", args.timeout),
        check_tool("OBS", "obs64"),
        {"name": "obs-websocket", "status": "skipped", "reason": "manual OBS configuration check required"},
        check_tool("FFmpeg", "ffmpeg"),
        {"name": "Worker config", "status": "available", "worker_type": "pc_game"},
        {"name": "PC Game Worker dry-run", "status": "skipped", "reason": "run manually after game/OBS setup"},
    ]
    print_json(
        summarize(
            role="pc_game_worker",
            machine_name=args.machine_name or "W1",
            checks=checks,
            recommendations=["high 桶真实采集必须由行为包 + OBS/FFmpeg 抽帧完成。"],
        )
    )


if __name__ == "__main__":
    main()
