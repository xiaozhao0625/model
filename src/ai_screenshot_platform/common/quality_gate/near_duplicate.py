from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class NearDuplicateDecision:
    image_id: str
    is_near_duplicate: bool
    duplicate_of: str | None = None
    distance: int = 0


class NearDuplicateIndex:
    def __init__(self, max_hamming_distance: int = 4) -> None:
        self.max_hamming_distance = max_hamming_distance
        self._items: dict[str, str] = {}

    def check_and_register(self, image_id: str, image_bytes: bytes) -> NearDuplicateDecision:
        digest = hashlib.sha256(image_bytes).hexdigest()
        for existing_id, existing_digest in self._items.items():
            distance = self._hamming_hex(digest, existing_digest)
            if distance <= self.max_hamming_distance:
                return NearDuplicateDecision(image_id, True, existing_id, distance)
        self._items[image_id] = digest
        return NearDuplicateDecision(image_id, False)

    def _hamming_hex(self, left: str, right: str) -> int:
        return sum(a != b for a, b in zip(left, right))
