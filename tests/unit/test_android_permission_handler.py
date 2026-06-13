from __future__ import annotations

from ai_screenshot_platform.workers.android.permission_handler import PermissionHandler


def test_permission_handler_defaults_to_request_manual():
    decision = PermissionHandler().handle_permission_popup("<node text='Allow camera' />")

    assert decision.action == "request_manual"
