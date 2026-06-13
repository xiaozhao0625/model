from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MasterSettings:
    database_url: str = "sqlite:///runs/master/master.db"
    redis_url: str = "memory://"
    env: str = "development"
    data_root: str | Path = "runs/master"

    @classmethod
    def from_env(cls) -> MasterSettings:
        return cls(
            database_url=os.environ.get("DATABASE_URL", cls.database_url),
            redis_url=os.environ.get("REDIS_URL", cls.redis_url),
            env=os.environ.get("APP_ENV", cls.env),
            data_root=os.environ.get("DATA_ROOT", str(cls.data_root)),
        )

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
