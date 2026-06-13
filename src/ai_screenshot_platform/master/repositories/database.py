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
                target_min INTEGER NOT NULL DEFAULT 1000,
                target_max INTEGER NOT NULL DEFAULT 5000,
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
                machine_name TEXT,
                capabilities TEXT NOT NULL,
                state TEXT NOT NULL,
                heartbeat TEXT,
                current_run_id TEXT
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
        self._ensure_column("runs", "target_min", "INTEGER NOT NULL DEFAULT 1000")
        self._ensure_column("runs", "target_max", "INTEGER NOT NULL DEFAULT 5000")
        self._ensure_column("workers", "machine_name", "TEXT")
        self._ensure_column("workers", "current_run_id", "TEXT")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def _ensure_column(self, table_name: str, column_name: str, definition: str) -> None:
        columns = {
            str(row["name"])
            for row in self.connection.execute(f"PRAGMA table_info({table_name})")
        }
        if column_name not in columns:
            self.connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
            )
