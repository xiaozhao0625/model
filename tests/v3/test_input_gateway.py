import json

from ai_screenshot_platform.v3.action.click_executor import ClickExecutor
from ai_screenshot_platform.v3.action.input_gateway import blocked_reason_for_action, input_gateway_readiness_from_diagnosis
from ai_screenshot_platform.v3.schemas import ActionDecision, FusedCandidate


def test_input_gateway_reports_getcursorpos_access_denied_blocker():
    readiness = input_gateway_readiness_from_diagnosis(
        {
            "same_desktop_session_ready": True,
            "same_integrity_ready": True,
            "interactive_desktop_ready": True,
            "get_cursor_pos": {"ok": False, "error": "GetCursorPos failed: Access is denied"},
            "set_cursor_pos": {"ok": False, "error": "not_tested"},
            "sendinput": {"callable": False},
            "mouse_event": {"callable": False},
            "pyautogui": {"available": False},
        }
    )

    assert readiness.cursor_read_ready is False
    assert readiness.cursor_read_access_denied is True
    assert readiness.keyboard_input_ready is False
    assert readiness.mouse_move_ready is False
    assert readiness.mouse_click_ready is False
    assert readiness.input_gateway_ready is False
    assert readiness.click_backend == "dry_run_backend"
    assert "cursor_read_access_denied" in readiness.blockers


def test_input_gateway_selects_audited_sendinput_fallback_when_cursor_probe_fails():
    readiness = input_gateway_readiness_from_diagnosis(
        {
            "same_desktop_session_ready": True,
            "same_integrity_ready": True,
            "interactive_desktop_ready": True,
            "get_cursor_pos": {"ok": False, "error": "GetCursorPos failed: Access is denied"},
            "set_cursor_pos": {"ok": True},
            "sendinput": {"callable": True},
            "mouse_event": {"callable": True},
            "pyautogui": {"available": False},
            "target_process": {"found": True, "foreground": True},
        }
    )

    assert readiness.cursor_read_ready is False
    assert readiness.cursor_read_access_denied is True
    assert readiness.keyboard_input_ready is True
    assert readiness.mouse_move_ready is True
    assert readiness.mouse_move_relative_ready is True
    assert readiness.mouse_click_ready is False
    assert readiness.input_gateway_ready is False
    assert readiness.click_backend == "dry_run_backend"
    assert "cursor_read_access_denied" in readiness.blockers
    assert blocked_reason_for_action("key_hold", readiness) is None
    assert blocked_reason_for_action("mouse_move_small", readiness) is None
    assert blocked_reason_for_action("mouse_move_relative", readiness) is None
    assert blocked_reason_for_action("mouse_click", readiness) == "cursor_read_access_denied"


def test_click_executor_audits_selected_backend():
    candidate = FusedCandidate(
        label="File",
        source="ocr_box",
        bbox=[10, 10, 40, 30],
        click_x=25,
        click_y=20,
        confidence=0.95,
        reason="safe menu",
        final_score=0.9,
    )
    decision = ActionDecision(action="click", allowed=True, reason="allowed", candidate=candidate)
    clicks: list[tuple[int, int]] = []

    result = ClickExecutor(
        allow_real_click=True,
        click_backend=lambda x, y: clicks.append((x, y)),
        click_backend_name="win32_sendinput_backend",
    ).execute(decision)

    assert result["executed"] is True
    assert result["click_backend"] == "win32_sendinput_backend"
    assert clicks == [(25, 20)]


def test_click_executor_blocks_outside_target_client_area():
    candidate = FusedCandidate(
        label="Close",
        source="ocr_box",
        bbox=[0, 0, 20, 20],
        click_x=5,
        click_y=5,
        confidence=0.95,
        reason="unsafe chrome",
        final_score=0.9,
    )
    decision = ActionDecision(action="click", allowed=True, reason="allowed", candidate=candidate)

    result = ClickExecutor(
        allow_real_click=True,
        click_backend=lambda x, y: None,
        click_backend_name="win32_sendinput_backend",
        target_client_rect=(20, 40, 300, 300),
    ).execute(decision)

    assert result["executed"] is False
    assert result["status"] == "blocked"
    assert result["reason"] == "outside_target_client_area"
    assert result["click_backend"] == "win32_sendinput_backend"


def test_input_gateway_readiness_json_shape_is_serializable():
    readiness = input_gateway_readiness_from_diagnosis(
        {
            "same_desktop_session_ready": True,
            "same_integrity_ready": True,
            "interactive_desktop_ready": True,
            "get_cursor_pos": {"ok": True},
            "set_cursor_pos": {"ok": True},
            "sendinput": {"callable": True},
            "mouse_event": {"callable": True},
            "pyautogui": {"available": False},
            "target_process": {"found": True, "foreground": True},
        }
    )

    payload = readiness.model_dump()

    assert json.loads(json.dumps(payload))["input_gateway_ready"] is True
    assert payload["click_backend"] == "computer_use_backend"
    assert payload["keyboard_input_ready"] is True
    assert payload["mouse_move_ready"] is True
    assert payload["mouse_move_relative_ready"] is True
    assert payload["target_window_found"] is True
    assert payload["target_window_foreground"] is True
