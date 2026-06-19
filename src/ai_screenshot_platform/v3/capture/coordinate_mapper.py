from __future__ import annotations


def map_bbox_to_click(bbox: list[int]) -> tuple[int, int]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain [x1, y1, x2, y2]")
    return (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2
