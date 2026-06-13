from __future__ import annotations

from ai_screenshot_platform.workers.android.input_controller import AndroidInputController


def test_android_input_controller_blocks_out_of_bounds_and_text_default():
    controller = AndroidInputController(screen_width=100, screen_height=100)

    assert controller.tap(101, 1).status == "blocked"
    assert controller.text("hello").status == "blocked"
