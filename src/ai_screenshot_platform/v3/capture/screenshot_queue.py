from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenshotQueueItem:
    image_id: str
    path: str
    source: str


class ScreenshotQueue:
    def __init__(self, max_length: int = 1000) -> None:
        self.max_length = max_length
        self._items: deque[ScreenshotQueueItem] = deque()

    def push(self, item: ScreenshotQueueItem) -> bool:
        if len(self._items) >= self.max_length:
            return False
        self._items.append(item)
        return True

    def pop(self) -> ScreenshotQueueItem | None:
        return self._items.popleft() if self._items else None

    def __len__(self) -> int:
        return len(self._items)
