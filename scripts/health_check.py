"""
Health check script for Whisp API.
Verifies the app is running and database calls are working correctly.

Usage:
    # Check against local server (default)
    python -m scripts.health_check

    # Check against a custom URL
    python -m scripts.health_check --url http://your-server:8001

    # Run DB checks directly (no running server needed)
    python -m scripts.health_check --db-only
"""

import argparse
import sys
import time

import httpx
from sqlalchemy import text

from app.core.db.engine import engine, SessionLocal


def check_db_connection() -> bool:
    """Verify we can connect to the database and execute a basic query."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row[0] == 1, f"Expected 1, got {row[0]}"
        print("[OK] Database connection")
        return True
    except Exception as e:
        print(f"[FAIL] Database connection: {e}")
        return False


def check_tables_exist() -> bool:
    """Verify all expected application tables exist in the database."""
    expected_tables = [
        "users",
        "expenses",
        "categories",
        "reminders",
        "cache",
    ]
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            existing = {row[0] for row in result.fetchall()}

        missing = [t for t in expected_tables if t not in existing]
        if missing:
            print(f"[FAIL] Missing tables: {', '.join(missing)}")
            return False
        print(f"[OK] All {len(expected_tables)} tables present")
        return True
    except Exception as e:
        print(f"[FAIL] Table check: {e}")
        return False


def check_table_row_counts() -> bool:
    """Read row counts from each table to verify queries work."""
    tables = [
        "users",
        "expenses",
        "categories",
        "reminders",
    ]
    try:
        with SessionLocal() as session:
            for table in tables:
                count = session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")  # noqa: S608 – table names are hardcoded above
                ).scalar()
                print(f"       {table}: {count} rows")
        print("[OK] Table row counts readable")
        return True
    except Exception as e:
        print(f"[FAIL] Table row counts: {e}")
        return False


def check_db_write_rollback() -> bool:
    """Verify we can start a transaction, write, and rollback (no side effects)."""
    try:
        with SessionLocal() as session:
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS _health_check_tmp (id INTEGER PRIMARY KEY)"
                )
            )
            session.execute(text("INSERT INTO _health_check_tmp (id) VALUES (1)"))
            session.rollback()
            session.execute(text("DROP TABLE IF EXISTS _health_check_tmp"))
            session.commit()
        print("[OK] Database write + rollback")
        return True
    except Exception as e:
        print(f"[FAIL] Database write + rollback: {e}")
        return False


def check_api_demo(base_url: str) -> bool:
    """Hit the /demo endpoint and verify the response."""
    try:
        resp = httpx.get(f"{base_url}/demo", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        assert data.get("message") == "Hello World", f"Unexpected response: {data}"
        print(f"[OK] GET /demo ({resp.status_code})")
        return True
    except httpx.ConnectError:
        print(f"[FAIL] GET /demo: cannot connect to {base_url} (is the server running?)")
        return False
    except Exception as e:
        print(f"[FAIL] GET /demo: {e}")
        return False


def check_api_docs(base_url: str) -> bool:
    """Verify the OpenAPI docs endpoint is reachable."""
    try:
        resp = httpx.get(f"{base_url}/docs", timeout=10)
        resp.raise_for_status()
        print(f"[OK] GET /docs ({resp.status_code})")
        return True
    except httpx.ConnectError:
        print(f"[FAIL] GET /docs: cannot connect to {base_url}")
        return False
    except Exception as e:
        print(f"[FAIL] GET /docs: {e}")
        return False


def run_db_checks() -> list[bool]:
    print("=== Database Checks ===")
    return [
        check_db_connection(),
        check_tables_exist(),
        check_table_row_counts(),
        check_db_write_rollback(),
    ]


def run_api_checks(base_url: str) -> list[bool]:
    print(f"\n=== API Checks ({base_url}) ===")
    return [
        check_api_demo(base_url),
        check_api_docs(base_url),
    ]


def main():
    parser = argparse.ArgumentParser(description="Whisp API health check")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8001",
        help="Base URL of the running Whisp API (default: http://127.0.0.1:8001)",
    )
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Only run database checks (no running server needed)",
    )
    args = parser.parse_args()

    print(f"Whisp Health Check — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = run_db_checks()

    if not args.db_only:
        results.extend(run_api_checks(args.url))

    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 30}")
    print(f"Result: {passed}/{total} checks passed")

    if all(results):
        print("All systems operational.")
        sys.exit(0)
    else:
        print("Some checks failed — see above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
