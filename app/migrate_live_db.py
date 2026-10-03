# migrate_live_db.py
import os


def migrate():
    database_url = os.environ.get("DATABASE_URL", "")

    if database_url.startswith("postgres"):
        print("Postgres detected - SQLAlchemy handles table creation")
        return

    # Legacy SQLite migration path
    import sqlite3
    DB_PATH = os.environ.get("SQLITE_PATH", "./data/receipts.db")
    if not os.path.exists(DB_PATH):
        print(f"SQLite not found at {DB_PATH} - skipping migration")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batches (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        status TEXT DEFAULT 'created',
        total_files INTEGER DEFAULT 0,
        processed_files INTEGER DEFAULT 0,
        failed_files INTEGER DEFAULT 0,
        progress_percent REAL DEFAULT 0.0,
        total_amount REAL DEFAULT 0.0,
        avg_confidence REAL DEFAULT 0.0,
        name TEXT,
        description TEXT,
        tags TEXT,
        error_log TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP
    )
    """)

    cursor.execute("PRAGMA table_info(receipts)")
    columns = [col[1] for col in cursor.fetchall()]

    new_columns = [
        ("batch_id", "TEXT"),
        ("storage_path", "TEXT"),
        ("raw_document_ai_json", "TEXT"),
        ("normalized_json", "TEXT"),
        ("error_message", "TEXT"),
        ("file_size", "INTEGER"),
        ("manually_edited", "INTEGER DEFAULT 0"),
        ("client_address", "TEXT"),
        ("due_date", "TEXT"),
        ("tax_type", "TEXT"),
        ("tax_year", "TEXT"),
        ("notes", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE receipts ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")

    conn.commit()
    conn.close()
    print("SQLite migration complete!")


if __name__ == "__main__":
    migrate()
