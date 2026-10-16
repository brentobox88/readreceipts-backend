# migrate_live_db.py
import os


# Columns that may need to be added to existing tables.
# Format: (table_name, column_name, column_type_sql)
NEW_COLUMNS = [
    ("receipts", "batch_id", "TEXT"),
    ("receipts", "storage_path", "TEXT"),
    ("receipts", "raw_document_ai_json", "TEXT"),
    ("receipts", "normalized_json", "TEXT"),
    ("receipts", "error_message", "TEXT"),
    ("receipts", "file_size", "INTEGER"),
    ("receipts", "manually_edited", "INTEGER DEFAULT 0"),
    ("receipts", "client_address", "TEXT"),
    ("receipts", "due_date", "TEXT"),
    ("receipts", "tax_type", "TEXT"),
    ("receipts", "tax_year", "TEXT"),
    ("receipts", "notes", "TEXT"),
    ("receipts", "merchant_name_en", "TEXT"),
    ("receipts", "line_items_count", "INTEGER"),
    ("receipts", "file_bytes", "BYTEA"),
]


def migrate():
    database_url = os.environ.get("DATABASE_URL", "")

    if database_url.startswith("postgres"):
        _migrate_postgres(database_url)
        return

    _migrate_sqlite()


def _migrate_postgres(database_url):
    """Add missing columns to Postgres tables. Safe to run on every startup."""
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed - skipping Postgres migration")
        return

    # SQLAlchemy-style postgres:// URLs need to become postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    try:
        conn = psycopg2.connect(database_url)
    except Exception as e:
        print(f"Could not connect to Postgres for migration: {e}")
        return

    try:
        cursor = conn.cursor()

        # Create batches table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'created',
            total_files INTEGER DEFAULT 0,
            processed_files INTEGER DEFAULT 0,
            failed_files INTEGER DEFAULT 0,
            progress_percent REAL DEFAULT 0.0,
            total_amount REAL DEFAULT 0.0,
            avg_confidence REAL DEFAULT 0.0,
            name VARCHAR(255),
            description TEXT,
            tags TEXT,
            error_log TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
        """)
        print("Batches table created or already exists")

        # Get existing columns on receipts
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'receipts'
        """)
        existing = {row[0] for row in cursor.fetchall()}
        print(f"Existing columns: {sorted(existing)}")

        # Add missing columns
        for table, col_name, col_type in NEW_COLUMNS:
            if col_name not in existing:
                try:
                    cursor.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_name} {col_type}')
                    print(f"Added column: {col_name}")
                except Exception as e:
                    print(f"Failed to add {col_name}: {e}")
            else:
                print(f"Column already exists: {col_name}")

        conn.commit()
        print("Postgres migration complete!")
    except Exception as e:
        conn.rollback()
        print(f"Postgres migration error: {e}")
    finally:
        conn.close()


def _migrate_sqlite():
    """Legacy SQLite migration path (for local development)."""
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

    for table, col_name, col_type in NEW_COLUMNS:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")

    conn.commit()
    conn.close()
    print("SQLite migration complete!")


if __name__ == "__main__":
    migrate()