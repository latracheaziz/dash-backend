"""
migrate_add_nlp_fields.py
─────────────────────────────────────────────────────────────────────────────
One-time migration: adds sentiment, intent, priority columns to call_records.

Safe to run multiple times — skips columns that already exist.

Usage:
    python migrate_add_nlp_fields.py
─────────────────────────────────────────────────────────────────────────────
"""
import sqlite3
import sys
from pathlib import Path

# ── Locate the SQLite database ────────────────────────────────────────────────
# db.sqlite3 lives in the same directory as this script (backend/)
DB_PATH = Path(__file__).parent / "db.sqlite3"

NEW_COLUMNS = [
    ("sentiment", "VARCHAR(20)  DEFAULT 'neutral'"),
    ("intent",    "VARCHAR(30)  DEFAULT 'other'"),
    ("priority",  "VARCHAR(10)  DEFAULT 'medium'"),
]


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def run_migration(db_path: Path) -> None:
    if not db_path.exists():
        print(f"[migrate] Database not found at: {db_path}")
        print("[migrate] Start the FastAPI server once to auto-create it, then re-run.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    added = []
    for col_name, col_def in NEW_COLUMNS:
        if column_exists(cur, "call_records", col_name):
            print(f"[migrate] Column '{col_name}' already exists — skipping.")
        else:
            cur.execute(f"ALTER TABLE call_records ADD COLUMN {col_name} {col_def}")
            added.append(col_name)
            print(f"[migrate] Added column '{col_name}'.")

    conn.commit()
    conn.close()

    if added:
        print(f"\n[migrate] DONE. Added: {', '.join(added)}")
    else:
        print("\n[migrate] DONE. Nothing to migrate — all columns already present.")


if __name__ == "__main__":
    run_migration(DB_PATH)
