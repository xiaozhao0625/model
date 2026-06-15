from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.master.core.config import MasterSettings
from ai_screenshot_platform.master.repositories.database import MasterDatabase


TABLES_CHECKED = [
    "quality_reports",
    "quality_report_items",
    "ocr_reports",
    "ocr_risk_hits",
    "tool_health_snapshots",
    "android_runtime_snapshots",
    "behavior_candidates",
    "behavior_candidate_reviews",
    "behavior_candidate_rollbacks",
    "deployment_diagnostics",
]


def main() -> None:
    database_url = os.environ.get("DATABASE_URL") or _read_env_file_database_url()
    psql_path = os.environ.get("PSQL_PATH") or _read_env_file_value("PSQL_PATH")
    if not database_url:
        print(
            _json(
                {
                    "status": "skipped",
                    "reason": "DATABASE_URL is not configured",
                    "postgres_available": False,
                    "schema_ready": False,
                    "tables_checked": TABLES_CHECKED,
                    "psql_configured": bool(psql_path),
                }
            )
        )
        return

    parsed = urlparse(database_url.replace("postgresql+psycopg://", "postgresql://", 1))
    if parsed.scheme not in {"postgresql", "postgres"}:
        print(
            _json(
                {
                    "status": "skipped",
                    "reason": "DATABASE_URL is not PostgreSQL",
                    "dialect": parsed.scheme or "unknown",
                    "postgres_available": False,
                    "schema_ready": False,
                    "tables_checked": TABLES_CHECKED,
                    "psql_configured": bool(psql_path),
                }
            )
        )
        return

    database = None
    try:
        settings = MasterSettings(database_url=database_url, redis_url="memory://")
        database = MasterDatabase(settings)
        row = database.connection.execute(
            "SELECT current_database() AS database, current_user AS user"
        ).fetchone()
        existing = []
        for table_name in TABLES_CHECKED:
            found = database.connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = ?
                """,
                (table_name,),
            ).fetchone()
            if found is not None:
                existing.append(table_name)
        schema_ready = set(existing) == set(TABLES_CHECKED)
        print(
            _json(
                {
                    "status": "ok" if schema_ready else "schema_incomplete",
                    "database": row["database"],
                    "user": row["user"],
                    "dialect": "postgresql",
                    "postgres_available": True,
                    "schema_ready": schema_ready,
                    "tables_checked": TABLES_CHECKED,
                    "tables_found": existing,
                    "psql_configured": bool(psql_path),
                    "psql_path_exists": Path(psql_path).exists() if psql_path else False,
                }
            )
        )
    except Exception as exc:  # pragma: no cover - depends on local PostgreSQL state
        print(
            _json(
                {
                    "status": "failed",
                    "reason": _safe_reason(exc),
                    "database": parsed.path.lstrip("/") or None,
                    "user": parsed.username,
                    "dialect": "postgresql",
                    "postgres_available": False,
                    "schema_ready": False,
                    "tables_checked": TABLES_CHECKED,
                    "psql_configured": bool(psql_path),
                    "psql_path_exists": Path(psql_path).exists() if psql_path else False,
                }
            )
        )
    finally:
        if database is not None:
            database.close()


def _read_env_file_database_url() -> str | None:
    return _read_env_file_value("DATABASE_URL")


def _read_env_file_value(name: str) -> str | None:
    env_path = Path(".env")
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")
    return None


def _safe_reason(exc: Exception) -> str:
    message = str(exc)
    database_url = os.environ.get("DATABASE_URL") or _read_env_file_database_url()
    if database_url:
        message = message.replace(database_url, "<redacted_database_url>")
    return message


def _json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
