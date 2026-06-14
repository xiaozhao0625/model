from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ai_screenshot_platform.master.core.config import MasterSettings


class MasterDatabase:
    def __init__(self, settings: MasterSettings) -> None:
        self.settings = settings
        if settings.database_backend == "sqlite":
            sqlite_path = settings.sqlite_path
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(sqlite_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        elif settings.database_backend == "postgresql":
            self.connection = self._connect_postgres(settings.database_url)
        else:
            raise ValueError("unsupported database backend")
        self.initialize()

    @classmethod
    def from_sqlite_path(cls, path: str | Path) -> MasterDatabase:
        return cls(MasterSettings(database_url=f"sqlite:///{Path(path)}"))

    def initialize(self) -> None:
        if self.settings.database_backend == "postgresql":
            self._initialize_postgres()
            return
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS apps (
                app_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                platform TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                retry_round INTEGER NOT NULL,
                worker_id TEXT
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

            CREATE TABLE IF NOT EXISTS run_status_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                previous_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                operator_action TEXT NOT NULL,
                changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self._initialize_production_readiness_sqlite()
        self._ensure_column("apps", "created_at", "TEXT")
        self._ensure_column("runs", "target_min", "INTEGER NOT NULL DEFAULT 1000")
        self._ensure_column("runs", "target_max", "INTEGER NOT NULL DEFAULT 5000")
        self._ensure_column("runs", "worker_id", "TEXT")
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

    def _connect_postgres(self, database_url: str):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise ValueError("psycopg is required for PostgreSQL DATABASE_URL") from exc
        dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        return PostgresConnectionAdapter(psycopg.connect(dsn, row_factory=dict_row))

    def _initialize_postgres(self) -> None:
        for statement in _BASE_SCHEMA_POSTGRES + _READINESS_SCHEMA_POSTGRES:
            self.connection.execute(statement)
        self._ensure_postgres_column("runs", "target_min", "INTEGER NOT NULL DEFAULT 1000")
        self._ensure_postgres_column("runs", "target_max", "INTEGER NOT NULL DEFAULT 5000")
        self._ensure_postgres_column("runs", "worker_id", "TEXT")
        self._ensure_postgres_column("workers", "machine_name", "TEXT")
        self._ensure_postgres_column("workers", "current_run_id", "TEXT")
        self._ensure_postgres_column("apps", "created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
        self.connection.commit()

    def _ensure_postgres_column(self, table_name: str, column_name: str, definition: str) -> None:
        row = self.connection.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ?
              AND column_name = ?
            """,
            (table_name, column_name),
        ).fetchone()
        if row is not None:
            return
        try:
            self.connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {definition}"
            )
        except Exception:
            self.connection.rollback()

    def _initialize_production_readiness_sqlite(self) -> None:
        self.connection.executescript("\n".join(_READINESS_SCHEMA_SQLITE))


class PostgresConnectionAdapter:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def execute(self, sql: str, parameters: tuple | list | None = None):
        return self.connection.execute(sql.replace("?", "%s"), parameters)

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            statement = statement.strip()
            if statement:
                self.execute(statement)

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()


_BASE_SCHEMA_POSTGRES = [
    """
    CREATE TABLE IF NOT EXISTS apps (
        app_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        platform TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
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
                retry_round INTEGER NOT NULL,
                worker_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workers (
        worker_id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        machine_name TEXT,
        capabilities TEXT NOT NULL,
        state TEXT NOT NULL,
        heartbeat TEXT,
        current_run_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS images (
        image_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        bucket TEXT NOT NULL,
        path TEXT NOT NULL,
        hash TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS uploads (
        upload_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS run_status_events (
        id SERIAL PRIMARY KEY,
        run_id TEXT NOT NULL,
        previous_status TEXT NOT NULL,
        new_status TEXT NOT NULL,
        operator_action TEXT NOT NULL,
        changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


_READINESS_SCHEMA_SQLITE = [
    """
    CREATE TABLE IF NOT EXISTS quality_reports (
        run_id TEXT PRIMARY KEY,
        app_id TEXT NOT NULL,
        total_images INTEGER NOT NULL DEFAULT 0,
        accepted_count INTEGER NOT NULL DEFAULT 0,
        rejected_count INTEGER NOT NULL DEFAULT 0,
        quality_pass_rate REAL NOT NULL DEFAULT 0,
        black_screen_count INTEGER NOT NULL DEFAULT 0,
        white_screen_count INTEGER NOT NULL DEFAULT 0,
        blurry_count INTEGER NOT NULL DEFAULT 0,
        wrong_window_count INTEGER NOT NULL DEFAULT 0,
        browser_chrome_count INTEGER NOT NULL DEFAULT 0,
        taskbar_count INTEGER NOT NULL DEFAULT 0,
        near_duplicate_count INTEGER NOT NULL DEFAULT 0,
        ocr_risk_hit_count INTEGER NOT NULL DEFAULT 0,
        reject_reason_distribution TEXT NOT NULL DEFAULT '{}',
        bucket_distribution TEXT NOT NULL DEFAULT '{}',
        source_path TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS quality_report_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        image_id TEXT,
        bucket TEXT,
        accepted INTEGER NOT NULL DEFAULT 0,
        reject_reason TEXT,
        quality_flags TEXT NOT NULL DEFAULT '[]',
        source_path TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ocr_reports (
        run_id TEXT PRIMARY KEY,
        app_id TEXT NOT NULL,
        provider TEXT NOT NULL,
        available INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL,
        risk_hits TEXT NOT NULL DEFAULT '[]',
        scene_hints TEXT NOT NULL DEFAULT '[]',
        unavailable_reason TEXT,
        paddleocr_status TEXT NOT NULL DEFAULT 'unknown',
        easyocr_status TEXT NOT NULL DEFAULT 'unknown',
        source_path TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ocr_risk_hits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        risk_type TEXT NOT NULL,
        text_excerpt TEXT,
        confidence REAL NOT NULL DEFAULT 0,
        source_path TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_health_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_name TEXT,
        worker_id TEXT,
        worker_type TEXT,
        status TEXT NOT NULL,
        tools TEXT NOT NULL DEFAULT '{}',
        master_ready TEXT NOT NULL DEFAULT '{}',
        worker_ready TEXT NOT NULL DEFAULT '{}',
        source_path TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS android_runtime_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id TEXT,
        profile_id TEXT,
        adb_available INTEGER NOT NULL DEFAULT 0,
        devices TEXT NOT NULL DEFAULT '[]',
        selected_device TEXT,
        screencap_status TEXT NOT NULL DEFAULT 'unknown',
        ui_dump_status TEXT NOT NULL DEFAULT 'unknown',
        ocr_fallback_status TEXT NOT NULL DEFAULT 'unknown',
        input_status TEXT NOT NULL DEFAULT 'unknown',
        skipped_reason TEXT,
        source_path TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS behavior_candidates (
        candidate_pack_id TEXT PRIMARY KEY,
        base_pack_id TEXT NOT NULL,
        game_type TEXT NOT NULL,
        version TEXT NOT NULL,
        status TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 0,
        issues TEXT NOT NULL DEFAULT '[]',
        recommendations TEXT NOT NULL DEFAULT '[]',
        rollback_target TEXT NOT NULL,
        created_from_run_id TEXT NOT NULL,
        pack_content TEXT NOT NULL DEFAULT '{}',
        source_path TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS behavior_candidate_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_pack_id TEXT NOT NULL,
        decision TEXT NOT NULL,
        reviewer TEXT,
        reason TEXT,
        enabled_after_review INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS behavior_candidate_rollbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_pack_id TEXT NOT NULL,
        rollback_target TEXT NOT NULL,
        reason TEXT,
        reviewer TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS deployment_diagnostics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_name TEXT,
        role TEXT,
        status TEXT NOT NULL,
        report_type TEXT NOT NULL,
        payload TEXT NOT NULL DEFAULT '{}',
        source_path TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
]


_READINESS_SCHEMA_POSTGRES = [
    statement.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    for statement in _READINESS_SCHEMA_SQLITE
]
