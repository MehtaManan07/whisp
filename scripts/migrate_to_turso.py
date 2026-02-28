"""
Migrate all data from local whisp.db (SQLite) to Turso (libSQL).

Usage:
    # Dry run — show what would be migrated, write nothing
    python -m scripts.migrate_to_turso --dry-run

    # Live run — migrate all data
    python -m scripts.migrate_to_turso

    # Specify a custom local DB path
    python -m scripts.migrate_to_turso --sqlite-path /path/to/whisp.db
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FK-safe insertion order.
# Categories needs two passes (parents before children), handled specially.
TABLE_ORDER = [
    "alembic_version",
    "cache",
    "users",
    "categories",
    "expenses",
    "reminders",
    "deodap_order_emails",
    "deodap_order_items",
]


def _get_table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def _count_source(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _count_target(target_conn, table: str) -> int:
    try:
        return target_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except Exception:
        return -1  # table might not exist yet


def _table_exists(target_conn, table: str) -> bool:
    row = target_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _migrate_table(
    src: sqlite3.Connection,
    dst,
    table: str,
    dry_run: bool,
    where_clause: str = "",
    where_params: tuple = (),
) -> dict:
    """
    Copy rows from src sqlite3 connection to dst (raw libsql connection).
    Returns {"inserted": int, "skipped": int, "errors": int}.
    """
    columns = _get_table_columns(src, table)
    col_list = ", ".join(columns)
    placeholders = ", ".join("?" * len(columns))

    query = f"SELECT {col_list} FROM {table}"
    if where_clause:
        query += f" WHERE {where_clause}"

    rows = src.execute(query, where_params).fetchall()
    total = len(rows)

    if dry_run:
        logger.info(f"  [DRY RUN] {table}: would insert {total} row(s)")
        if total and total <= 5:
            for r in rows:
                logger.info(f"    {dict(zip(columns, r))}")
        elif total:
            logger.info(f"    (showing first 3)")
            for r in rows[:3]:
                logger.info(f"    {dict(zip(columns, r))}")
        return {"inserted": 0, "skipped": total, "errors": 0}

    inserted = 0
    skipped = 0
    errors = 0

    insert_sql = f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"

    for row in rows:
        try:
            # Convert sqlite3.Row to tuple for libsql compatibility
            row_tuple = tuple(row)
            dst.execute(insert_sql, row_tuple)
            inserted += 1
        except Exception as e:
            logger.warning(f"  Error inserting row into {table}: {e} | row={dict(zip(columns, row))}")
            errors += 1

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


def migrate(sqlite_path: str, dry_run: bool) -> None:
    src_path = Path(sqlite_path)
    if not src_path.exists():
        logger.error(f"Source SQLite file not found: {src_path}")
        sys.exit(1)

    logger.info(f"Source DB: {src_path}")
    logger.info(f"Mode: {'DRY RUN (no writes)' if dry_run else 'LIVE (writing to Turso)'}")
    logger.info("=" * 60)

    # Connect to local SQLite
    src = sqlite3.connect(str(src_path))
    src.row_factory = sqlite3.Row

    # Connect to Turso via raw libsql driver (bypass SQLAlchemy for raw INSERT OR IGNORE)
    from app.core.config import config
    import libsql_experimental as libsql

    turso_url = config.turso_database_url
    turso_token = config.turso_auth_token

    if not dry_run:
        dst = libsql.connect(turso_url, auth_token=turso_token)
    else:
        dst = None

    # Pre-flight: verify Turso tables exist
    if not dry_run:
        missing = []
        for table in TABLE_ORDER:
            check = dst.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if check is None:
                missing.append(table)
        if missing:
            logger.error(
                f"Missing tables in Turso: {missing}\n"
                "Run `alembic upgrade head` against Turso before migrating data."
            )
            src.close()
            dst.close()
            sys.exit(1)

    totals = {"inserted": 0, "skipped": 0, "errors": 0}

    for table in TABLE_ORDER:
        src_count = _count_source(src, table)
        logger.info(f"\n[{table}] source rows: {src_count}")

        if src_count == 0:
            logger.info(f"  Skipping — no rows in source")
            continue

        if table == "categories":
            # Two-pass: parents first (parent_id IS NULL), then children
            logger.info("  Pass 1: inserting root categories (parent_id IS NULL)")
            r1 = _migrate_table(src, dst, table, dry_run, "parent_id IS NULL")

            logger.info("  Pass 2: inserting child categories (parent_id IS NOT NULL)")
            r2 = _migrate_table(src, dst, table, dry_run, "parent_id IS NOT NULL")

            result = {
                "inserted": r1["inserted"] + r2["inserted"],
                "skipped": r1["skipped"] + r2["skipped"],
                "errors": r1["errors"] + r2["errors"],
            }
        else:
            result = _migrate_table(src, dst, table, dry_run)

        if not dry_run:
            dst.commit()
            logger.info(
                f"  inserted={result['inserted']}  skipped={result['skipped']}  errors={result['errors']}"
            )

        for k in totals:
            totals[k] += result[k]

    src.close()
    if dst:
        dst.close()

    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION SUMMARY")
    if dry_run:
        logger.info("  (DRY RUN — nothing was written)")
        # In dry run, skipped = rows that would have been inserted
        total_rows = sum(
            _count_source(sqlite3.connect(str(src_path)), t)
            for t in TABLE_ORDER
        )
        logger.info(f"  Total rows that would be migrated: {total_rows}")
    else:
        logger.info(f"  Total inserted : {totals['inserted']}")
        logger.info(f"  Total skipped  : {totals['skipped']}")
        logger.info(f"  Total errors   : {totals['errors']}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Migrate whisp.db data to Turso")
    parser.add_argument(
        "--sqlite-path",
        default="whisp.db",
        help="Path to local SQLite file (default: whisp.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without writing any data",
    )
    args = parser.parse_args()
    migrate(args.sqlite_path, args.dry_run)


if __name__ == "__main__":
    main()
