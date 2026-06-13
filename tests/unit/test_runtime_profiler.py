from __future__ import annotations

from ai_screenshot_platform.common.runtime_profiler.profiler import RuntimeProfiler


def test_runtime_profiler_outputs_profile_from_metadata():
    profile = RuntimeProfiler().profile({"platform_type": "web", "worker_type": "web", "content_area_only": True})

    assert profile.platform_type == "web"
    assert profile.recommended_bucket == "low"
    assert profile.content_area_only is True
