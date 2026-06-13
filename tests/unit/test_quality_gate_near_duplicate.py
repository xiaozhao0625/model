from __future__ import annotations

from ai_screenshot_platform.common.quality_gate.near_duplicate import NearDuplicateIndex


def test_near_duplicate_detects_same_and_small_delta_bytes():
    index = NearDuplicateIndex(max_hamming_distance=4)

    first = index.check_and_register("img1", b"abcdef")
    second = index.check_and_register("img2", b"abcdef")

    assert first.is_near_duplicate is False
    assert second.is_near_duplicate is True
    assert second.duplicate_of == "img1"
