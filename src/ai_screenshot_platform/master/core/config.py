from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MasterSettings:
    database_url: str = "sqlite:///runs/master/master.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    env: str = "development"
    data_root: str | Path = "runs/master"
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:6137",
        "http://localhost:6137",
        "http://192.168.1.18:6137",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://192.168.1.18:5173",
    )

    @classmethod
    def from_env(cls) -> MasterSettings:
        _load_dotenv_without_override(Path.cwd() / ".env")
        cors_origins = tuple(
            origin.strip()
            for origin in os.environ.get("MASTER_CORS_ORIGINS", ",".join(cls.cors_origins)).split(",")
            if origin.strip()
        )
        return cls(
            database_url=os.environ.get("DATABASE_URL", cls.database_url),
            redis_url=os.environ.get("REDIS_URL", cls.redis_url),
            env=os.environ.get("APP_ENV", cls.env),
            data_root=os.environ.get("DATA_ROOT", str(cls.data_root)),
            cors_origins=cors_origins,
        )

    @property
    def database_backend(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            return "sqlite"
        if self.database_url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
            return "postgresql"
        return "unknown"

    @property
    def sqlite_path(self) -> Path:
        if self.database_backend != "sqlite":
            raise ValueError("sqlite_path is only available for sqlite database_url")
        return Path(self.database_url.removeprefix("sqlite:///")).resolve()


def _load_dotenv_without_override(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value
