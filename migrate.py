"""
Database migration helper for SQLite.
Adds any missing columns or tables that SQLAlchemy's create_all cannot handle
for existing databases (since SQLite doesn't support ALTER TABLE ADD COLUMN via create_all).

Run: python migrate.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "office_management.db")

MIGRATIONS = [
    # (table, column_name, column_definition)
    ("employees", "office_id", "INTEGER REFERENCES offices(id)"),
    ("employees", "rank_id",   "INTEGER REFERENCES ranks(id)"),
]


def run_migrations():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. It will be created on first run.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for table, column, definition in MIGRATIONS:
        cur.execute(f"PRAGMA table_info({table})")
        existing_cols = [r[1] for r in cur.fetchall()]
        if column not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                print(f"✓ [{table}] Added column: {column}")
            except Exception as e:
                print(f"✗ [{table}] Failed to add {column}: {e}")
        else:
            print(f"  [{table}] Column already exists: {column}")

    conn.commit()
    conn.close()
    print("\n✓ Migration complete!")


if __name__ == "__main__":
    run_migrations()
