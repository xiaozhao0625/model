from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class DedupCheckResult:
    is_duplicate: bool
    duplicate_of: str | None = None


class ContentHashDedupIndex:
    def __init__(self) -> None:
        self._hash_to_image_id: dict[str, str] = {}

    @staticmethod
    def calculate_hash(image_bytes: bytes) -> str:
        return sha256(image_bytes).hexdigest()

    def register(self, content_hash: str, image_id: str) -> None:
        self._hash_to_image_id.setdefault(content_hash, image_id)

    def check(self, content_hash: str) -> DedupCheckResult:
        duplicate_of = self._hash_to_image_id.get(content_hash)
        if duplicate_of is None:
            return DedupCheckResult(is_duplicate=False)
        return DedupCheckResult(is_duplicate=True, duplicate_of=duplicate_of)
