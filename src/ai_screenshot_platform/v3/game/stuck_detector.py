from __future__ import annotations


class GameStuckDetector:
    def detect(self, observation: dict[str, object], recent_actions: list[dict[str, object]] | None = None) -> dict[str, object]:
        recent_actions = recent_actions or []
        forward_attempts = _recent_forward_attempts(recent_actions)
        visual_diff = float(observation.get("visual_diff_score") or 0.0)
        center_diff = float(observation.get("center_diff_score") or 0.0)
        near_duplicate_ratio = float(observation.get("near_duplicate_ratio") or 0.0)
        repeated_frame_count = int(observation.get("repeated_frame_count") or 0)
        accepted_unique_delta_recent = int(observation.get("accepted_unique_delta_recent") or 0)
        possible_wall = bool(observation.get("possible_wall_ahead"))
        stuck = bool(
            forward_attempts >= 3
            and (
                visual_diff < 0.08
                or center_diff < 0.05
                or near_duplicate_ratio > 0.7
                or accepted_unique_delta_recent == 0
                or repeated_frame_count >= 3
            )
        )
        reason = None
        recommended = None
        if stuck:
            reason = "forward_no_visual_change"
            recommended = "back_and_turn"
        elif possible_wall:
            reason = "high_center_edge_low_forward_motion"
            recommended = "turn_and_strafe"
        return {
            "stuck": stuck,
            "reason": reason,
            "recommended_recovery": recommended,
            "possible_wall_ahead": possible_wall,
            "forward_attempt_count": forward_attempts,
        }


def _recent_forward_attempts(recent_actions: list[dict[str, object]]) -> int:
    count = 0
    for action in recent_actions[-6:]:
        keys = action.get("keys")
        normalized = [str(key).upper() for key in keys] if isinstance(keys, list) else []
        if action.get("action_type") == "key_hold" and "W" in normalized:
            count += 1
    return count
