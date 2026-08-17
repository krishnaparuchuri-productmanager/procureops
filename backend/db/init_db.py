"""
init_db.py — Initialize the SQLite database for ProcureOps.

Creates the database file and all tables if they do not already exist.
Safe to run multiple times — uses IF NOT EXISTS on every table.

Usage:
    python backend/db/init_db.py          # from project root
    python init_db.py                     # from backend/db/
"""

import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

THIS_DIR = Path(__file__).resolve().parent          # .../backend/db/
BACKEND_DIR = THIS_DIR.parent                       # .../backend/
PROJECT_ROOT = BACKEND_DIR.parent                   # .../procureops/

DB_PATH = BACKEND_DIR / "db" / "procureops.db"

sys.path.insert(0, str(BACKEND_DIR))

from db.schema import ALL_TABLES


def get_db_path() -> Path:
    return DB_PATH


def init_db(db_path: Path | None = None) -> None:
    """Create the database file and all tables if they do not exist."""
    target = db_path or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    print(f"[init_db] Database path : {target}")

    conn = sqlite3.connect(target)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    try:
        with conn:
            for table_name, create_sql in ALL_TABLES:
                conn.execute(create_sql)
                print(f"[init_db] OK  Table ready : {table_name}")
    except sqlite3.Error as exc:
        print(f"[init_db] ERROR creating tables: {exc}", file=sys.stderr)
        raise
    finally:
        conn.close()

    print("[init_db] Database initialized successfully.")


def verify_tables(db_path: Path | None = None) -> list[str]:
    target = db_path or DB_PATH
    conn = sqlite3.connect(target)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()

    expected = {name for name, _ in ALL_TABLES}
    found = set(verify_tables())

    missing = expected - found
    print("\n[init_db] Verification:")
    for name in sorted(expected):
        status = "OK" if name in found else "MISSING"
        print(f"  {status}  {name}")

    if missing:
        print(f"\n[init_db] ERROR - missing tables: {missing}", file=sys.stderr)
        sys.exit(1)

    print("\n[init_db] All checks passed.")
