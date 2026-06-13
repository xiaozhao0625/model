from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.runtime.run_session import (  # noqa: E402
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.common.worker.behavior_worker import (  # noqa: E402
    BehaviorWorkerAgent,
)
from ai_screenshot_platform.common.worker.contracts import (  # noqa: E402
    WorkerCapability,
    WorkerProfile,
    WorkerState,
    WorkerTask,
    WorkerType,
)
from ai_screenshot_platform.workers.android.contracts import (  # noqa: E402
    AndroidTargetConfig,
)
from ai_screenshot_platform.workers.android.pipeline import (  # noqa: E402
    AndroidStubPipeline,
)
from ai_screenshot_platform.workers.android.stub_adapters import (  # noqa: E402
    StubAndroidDeviceAdapter,
    StubAndroidQualityAdapter,
    StubAndroidUiObserverAdapter,
)
from ai_screenshot_platform.workers.pc_app.contracts import (  # noqa: E402
    PcAppTargetConfig,
)
from ai_screenshot_platform.workers.pc_app.pipeline import (  # noqa: E402
    PcAppStubPipeline,
)
from ai_screenshot_platform.workers.pc_app.stub_adapters import (  # noqa: E402
    StubPcAppAutomationAdapter,
)
from ai_screenshot_platform.workers.pc_game.contracts import (  # noqa: E402
    CaptureSourceConfig,
)
from ai_screenshot_platform.workers.pc_game.pipeline import (  # noqa: E402
    PcGameStubPipeline,
)
from ai_screenshot_platform.workers.pc_game.stub_adapters import (  # noqa: E402
    StubFfmpegExtractAdapter,
    StubGameInputAdapter,
    StubObsCaptureAdapter,
)
from ai_screenshot_platform.workers.web.contracts import (  # noqa: E402
    WebTargetConfig,
)
from ai_screenshot_platform.workers.web.pipeline import WebStubPipeline  # noqa: E402
from ai_screenshot_platform.workers.web.stub_adapters import (  # noqa: E402
    StubWebAutomationAdapter,
)


BEHAVIOR_PACK_PATH = (
    REPO_ROOT / "configs" / "behavior_packs" / "fps_mock_v1.example.json"
)
WORKERS = [
    "pc_game_behavior",
    "pc_game_stub",
    "pc_app_stub",
    "web_stub",
    "android_stub",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all P4 worker mock flows.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--target-min", type=int, default=3)
    return parser.parse_args()


def make_session(
    root: Path,
    app_id: str,
    run_id: str,
    target_min: int,
) -> LocalRunSession:
    return LocalRunSession(
        RunSessionConfig(
            root_dir=root,
            app_id=app_id,
            run_id=run_id,
            target_min=target_min,
        )
    )


def run_pc_game_behavior(root: Path, target_min: int):
    profile = WorkerProfile(
        worker_id="p4-pc-game-behavior",
        machine_name="mock-machine",
        worker_type=WorkerType.PC_GAME,
        gpu_name="mock-gpu",
        capabilities={
            WorkerCapability.CAPTURE_HIGH,
            WorkerCapability.BEHAVIOR_PACK,
            WorkerCapability.OBS_CAPTURE,
            WorkerCapability.FFMPEG_EXTRACT,
        },
        state=WorkerState.IDLE,
        current_run_id=None,
    )
    task = WorkerTask(
        app_id="p4_pc_game_behavior",
        run_id="pc_game_behavior",
        app_type="pc_game",
        platform="windows",
        target_min=target_min,
        target_max=5000,
        bucket="high",
        root_dir=root,
        behavior_pack_path=BEHAVIOR_PACK_PATH,
        behavior_pack_id="fps_mock_v1",
        context=["match"],
    )
    return BehaviorWorkerAgent(profile).execute(task)


def run_pc_game_stub(root: Path, target_min: int):
    session = make_session(root, "p4_pc_game_stub", "pc_game_stub", target_min)
    pipeline = PcGameStubPipeline(
        session=session,
        obs_adapter=StubObsCaptureAdapter(output_dir=session.run_dir / "temp_video"),
        ffmpeg_adapter=StubFfmpegExtractAdapter(),
        input_adapter=StubGameInputAdapter(),
    )
    return pipeline.run(
        CaptureSourceConfig(
            source_name="p4-pc-game-stub",
            window_title="Mock PC Game",
            fps=30,
            width=1280,
            height=720,
        ),
        max_frames=target_min,
    )


def run_pc_app_stub(root: Path, target_min: int):
    session = make_session(root, "p4_pc_app_stub", "pc_app_stub", target_min)
    pipeline = PcAppStubPipeline(
        session=session,
        automation_adapter=StubPcAppAutomationAdapter(),
    )
    return pipeline.run(
        PcAppTargetConfig(
            app_id="p4_pc_app",
            window_title="Mock Desktop App",
            process_name="mock-app.exe",
            content_region={"x": 0, "y": 0, "width": 1024, "height": 768},
        )
    )


def run_web_stub(root: Path, target_min: int):
    session = make_session(root, "p4_web_stub", "web_stub", target_min)
    pipeline = WebStubPipeline(
        session=session,
        automation_adapter=StubWebAutomationAdapter(),
    )
    return pipeline.run(
        WebTargetConfig(
            app_id="p4_web_app",
            url="https://example.invalid/p4",
            viewport_width=1280,
            viewport_height=720,
        )
    )


def run_android_stub(root: Path, target_min: int):
    session = make_session(root, "p4_android_stub", "android_stub", target_min)
    pipeline = AndroidStubPipeline(
        session=session,
        device_adapter=StubAndroidDeviceAdapter(),
        ui_observer=StubAndroidUiObserverAdapter(),
        quality_adapter=StubAndroidQualityAdapter(),
    )
    return pipeline.run(
        AndroidTargetConfig(
            app_id="p4_android_app",
            package_name="com.example.p4",
            activity_name=".MainActivity",
            device_id="mock-android",
        )
    )


def summarize_result(result: Any) -> dict[str, Any]:
    return {
        "status": result.status.value,
        "valid_total": result.valid_total,
        "bucket_counts": {
            "fixed_count": result.fixed_count,
            "low_count": result.low_count,
            "high_count": result.high_count,
            "rejected_count": result.rejected_count,
        },
        "generated_files": {
            "summary": str(result.summary_path),
            "meta": str(result.run_dir / "meta.jsonl"),
            "run_log": str(result.run_dir / "run.log"),
        },
        "forbidden_files_absent": {
            "upload_manifest": not (result.run_dir / "upload_manifest.json").exists(),
        },
    }


def run_mock(root: Path, target_min: int) -> dict[str, Any]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    results = {
        "pc_game_behavior": run_pc_game_behavior(root, target_min),
        "pc_game_stub": run_pc_game_stub(root, target_min),
        "pc_app_stub": run_pc_app_stub(root, target_min),
        "web_stub": run_web_stub(root, target_min),
        "android_stub": run_android_stub(root, target_min),
    }
    summaries = {
        worker_name: summarize_result(result)
        for worker_name, result in results.items()
    }
    summaries["pc_game_behavior"]["generated_files"]["behavior_actions"] = str(
        results["pc_game_behavior"].behavior_actions_path
    )

    return {
        "workers": WORKERS,
        "final_status_by_worker": {
            worker_name: summaries[worker_name]["status"] for worker_name in WORKERS
        },
        "valid_total_by_worker": {
            worker_name: summaries[worker_name]["valid_total"]
            for worker_name in WORKERS
        },
        "bucket_counts_by_worker": {
            worker_name: summaries[worker_name]["bucket_counts"]
            for worker_name in WORKERS
        },
        "content_area_only_for_web": results["web_stub"].content_area_only,
        "generated_files": {
            worker_name: summaries[worker_name]["generated_files"]
            for worker_name in WORKERS
        },
        "forbidden_files_absent": {
            worker_name: summaries[worker_name]["forbidden_files_absent"]
            for worker_name in WORKERS
        },
    }


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            run_mock(Path(args.root), args.target_min),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
