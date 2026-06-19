from __future__ import annotations


SAFE_GAME_ACTIONS = ["wait", "wasd", "mouse_move_small", "space", "shift_short", "e_or_f_interact_low_frequency"]


def safe_game_explore_plan(enabled: bool = False) -> dict[str, object]:
    return {
        "enabled": enabled,
        "real_input_executed": False,
        "actions": SAFE_GAME_ACTIONS if enabled else [],
        "note": "Game explorer is disabled by default and never handles login, chat, payment, ranked, or matchmaking.",
    }
