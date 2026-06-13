from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_screenshot_platform.master.core.config import MasterSettings


class MasterDatabase:
    def __init__(self, settings: MasterSettings) -> None:
        self.settings = settings
        if settings.database_backend != "sqlite":
            raise ValueError(
                "P7 runtime supports sqlite execution; PostgreSQL is config-ready only"
            )
        sqlite_path = settings.sqlite_path
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(sqlite_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.initialize()

    @classmethod
    def from_sqlite_path(cls, path: str | Path) -> MasterDatabase:
        return cls(MasterSettings(database_url=f"sqlite:///{Path(path)}"))

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS apps (
                app_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                platform TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                app_id TEXT NOT NULL,
                status TEXT NOT NULL,
                valid_total INTEGER NOT NULL,
                fixed_count INTEGER NOT NULL,
                low_count INTEGER NOT NULL,
                high_count INTEGER NOT NULL,
                rejected_count INTEGER NOT NULL,
                retry_round INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workers (
                worker_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                state TEXT NOT NULL,
                heartbeat TEXT
            );

            CREATE TABLE IF NOT EXISTS images (
                image_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                bucket TEXT NOT NULL,
                path TEXT NOT NULL,
                hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS uploads (
                upload_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                status TEXT NOT NULL
            );
            """
        )
        self.connection.commit()
