from __future__ import annotations


ROLLBACK_SEQUENCE = ["esc", "alt_left", "backspace", "request_manual"]


def rollback_plan(reason: str) -> dict[str, object]:
    return {"reason": reason, "sequence": ROLLBACK_SEQUENCE, "real_input_required": False}
