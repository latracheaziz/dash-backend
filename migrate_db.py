"""
Migration: Add missing columns to call_records table.
Run once from the backend/ directory.
"""
import sqlite3

DB_PATH = "db.sqlite3"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check existing columns
cursor.execute("PRAGMA table_info(call_records)")
existing = {row[1] for row in cursor.fetchall()}
print("Existing columns:", existing)

# Columns to add if missing
needed = [
    ("status",      "TEXT DEFAULT 'Completed'"),
    ("transcript",  "TEXT"),
    ("rating",      "INTEGER DEFAULT 0"),
    ("explanation", "TEXT"),
    ("strengths",   "TEXT"),
    ("weaknesses",  "TEXT"),
    ("suggestions", "TEXT"),
]

for col, definition in needed:
    if col not in existing:
        sql = f"ALTER TABLE call_records ADD COLUMN {col} {definition}"
        print(f"Running: {sql}")
        cursor.execute(sql)
    else:
        print(f"Already exists: {col}")

conn.commit()
conn.close()
print("\nMigration complete. All required columns are present.")
