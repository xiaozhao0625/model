from __future__ import annotations

import hashlib
from pathlib import Path


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DuplicateFilter:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def check(self, path: str | Path) -> tuple[bool, str]:
        digest = file_sha256(path)
        if digest in self._seen:
            return False, digest
        self._seen.add(digest)
        return True, digest
