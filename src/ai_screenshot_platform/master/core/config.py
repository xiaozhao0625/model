from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MasterSettings:
    database_url: str = "sqlite:///master.db"
    redis_url: str = "memory://"
    env: str = "development"
    data_root: str | Path = "runs/master"

    @property
    def database_backend(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            return "sqlite"
        if self.database_url.startswith(("postgresql://", "postgres://")):
            return "postgresql"
        return "unknown"

    @property
    def sqlite_path(self) -> Path:
        if self.database_backend != "sqlite":
            raise ValueError("sqlite_path is only available for sqlite database_url")
        return Path(self.database_url.removeprefix("sqlite:///")).resolve()
