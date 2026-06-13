from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.runtime.run_session import (  # noqa: E402
    LocalRunSession,
    RunSessionConfig,
)
from ai_screenshot_platform.workers.web.contracts import WebTargetConfig  # noqa: E402
from ai_screenshot_platform.workers.web.health_check import (  # noqa: E402
    check_web_playwright_health,
)
from ai_screenshot_platform.workers.web.real_playwright_adapter import (  # noqa: E402
    RealPlaywrightWebAdapter,
)
from ai_screenshot_platform.workers.web.pipeline import WebStubPipeline  # noqa: E402


def main() -> None:
    health = check_web_playwright_health()
    if not health.available:
        print(
            json.dumps(
                {"status": "skipped", "tool": "playwright", "reason": health.reason},
                ensure_ascii=False,
            )
        )
        return

    root = REPO_ROOT / "runs" / "smoke_web_playwright"
    session = LocalRunSession(
        RunSessionConfig(root_dir=root, app_id="web_smoke", run_id="playwright", target_min=1)
    )
    adapter = RealPlaywrightWebAdapter(enabled=True)
    try:
        result = WebStubPipeline(session=session, automation_adapter=adapter).run(
            WebTargetConfig(
                app_id="web_smoke",
                url="data:text/html,<main><h1>P10 Smoke</h1></main>",
                viewport_width=800,
                viewport_height=600,
                content_area_only=True,
            )
        )
    finally:
        adapter.close()
    print(
        json.dumps(
            {
                "status": result.status.value,
                "valid_total": result.valid_total,
                "summary_path": str(result.summary_path),
                "content_area_only": result.content_area_only,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
