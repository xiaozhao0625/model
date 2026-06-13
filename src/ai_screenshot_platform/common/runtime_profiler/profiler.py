from __future__ import annotations

from typing import Any

from ai_screenshot_platform.common.runtime_profiler.contracts import RuntimeProfile


class RuntimeProfiler:
    def profile(self, metadata: dict[str, Any]) -> RuntimeProfile:
        platform_type = str(metadata.get("platform_type", "unknown"))
        worker_type = str(metadata.get("worker_type", platform_type))
        app_type = str(metadata.get("app_type", "unknown"))
        if worker_type == "pc_game" or app_type == "game":
            bucket = "high"
        else:
            bucket = "low"
        return RuntimeProfile(
            platform_type=platform_type,
            worker_type=worker_type,
            app_type=app_type,
            recommended_bucket=str(metadata.get("recommended_bucket", bucket)),
            content_area_only=bool(metadata.get("content_area_only", worker_type == "web")),
            capabilities=list(metadata.get("capabilities", [])),
            metadata=metadata,
        )
