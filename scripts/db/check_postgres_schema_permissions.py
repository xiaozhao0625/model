from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_screenshot_platform.master.core.config import MasterSettings
from ai_screenshot_platform.master.repositories.database import MasterDatabase


EXPECTED_COLUMNS = {
    "apps": ["created_at"],
    "runs": ["worker_id"],
    "workers": ["machine_name", "current_run_id"],
}
KEY_TABLES = {
    "apps",
    "runs",
    "workers",
    "images",
    "uploads",
    "run_status_events",
    "ocr_reports",
    "ocr_risk_hits",
    "quality_reports",
    "quality_report_items",
}
REQUIRED_DML = {"SELECT", "INSERT", "UPDATE", "DELETE"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PostgreSQL schema ownership and grants without printing secrets.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    report = collect_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0 if report["schema_ready"] else 1


def collect_report() -> dict[str, Any]:
    settings = MasterSettings.from_env()
    database = MasterDatabase(settings)
    connection = database.connection
    try:
        current_user = connection.execute("SELECT current_user").fetchone()["current_user"]
        tables = {
            row["tablename"]: row["tableowner"]
            for row in connection.execute(
                """
                SELECT tablename, tableowner
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            ).fetchall()
        }
        sequences = {
            row["sequencename"]: row["sequenceowner"]
            for row in connection.execute(
                """
                SELECT sequencename, sequenceowner
                FROM pg_sequences
                WHERE schemaname = 'public'
                ORDER BY sequencename
                """
            ).fetchall()
        }
        grants_by_table: dict[str, set[str]] = {}
        for row in connection.execute(
            """
            SELECT table_name, privilege_type
            FROM information_schema.role_table_grants
            WHERE grantee = current_user
              AND table_schema = 'public'
            ORDER BY table_name, privilege_type
            """
        ).fetchall():
            grants_by_table.setdefault(row["table_name"], set()).add(row["privilege_type"])

        sequence_grants = connection.execute(
            """
            SELECT object_schema, object_name, privilege_type
            FROM information_schema.role_usage_grants
            WHERE grantee = current_user
              AND object_schema = 'public'
            ORDER BY object_name, privilege_type
            """
        ).fetchall()

        missing_columns = {}
        for table_name, expected in EXPECTED_COLUMNS.items():
            existing = {
                row["column_name"]
                for row in connection.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = ?
                    """,
                    (table_name,),
                ).fetchall()
            }
            missing_columns[table_name] = [column for column in expected if column not in existing]

        migration_tables = [
            row["tablename"]
            for row in connection.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename LIKE '%migration%'
                ORDER BY tablename
                """
            ).fetchall()
        ]

        key_table_grants = {
            table: sorted(grants_by_table.get(table, set()))
            for table in sorted(KEY_TABLES & set(tables))
        }
        grant_gaps = {
            table: sorted(REQUIRED_DML - set(grants))
            for table, grants in key_table_grants.items()
            if REQUIRED_DML - set(grants)
        }
        owner_gaps = {
            table: owner
            for table, owner in tables.items()
            if table in KEY_TABLES and owner != current_user
        }

        schema_ready = (
            settings.database_backend == "postgresql"
            and not any(missing_columns.values())
            and "schema_migrations" in migration_tables
            and not grant_gaps
            and not owner_gaps
        )
        return {
            "backend": settings.database_backend,
            "current_user": current_user,
            "schema_ready": schema_ready,
            "tables": tables,
            "sequences": sequences,
            "migration_tables": migration_tables,
            "missing_expected_columns": missing_columns,
            "key_table_grants": key_table_grants,
            "grant_gaps": grant_gaps,
            "owner_gaps": owner_gaps,
            "sequence_usage_grants_count": len(sequence_grants),
            "secrets_printed": False,
        }
    finally:
        database.close()


def print_human(report: dict[str, Any]) -> None:
    print(f"backend: {report['backend']}")
    print(f"current_user: {report['current_user']}")
    print(f"schema_ready: {report['schema_ready']}")
    print(f"migration_tables: {', '.join(report['migration_tables']) or 'none'}")
    print(f"missing_expected_columns: {json.dumps(report['missing_expected_columns'], ensure_ascii=False)}")
    print(f"owner_gaps: {json.dumps(report['owner_gaps'], ensure_ascii=False)}")
    print(f"grant_gaps: {json.dumps(report['grant_gaps'], ensure_ascii=False)}")
    print("secrets_printed: false")


if __name__ == "__main__":
    raise SystemExit(main())
