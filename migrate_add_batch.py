# migrate_add_batch.py
import sqlite3
import os

DB_PATH = '/opt/render/project/src/data/receipts.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create batches table
    cursor.execute('''
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
    ''')
    
    # Add columns to receipts table if they don't exist
    cursor.execute('PRAGMA table_info(receipts)')
    columns = [col[1] for col in cursor.fetchall()]
    
    new_columns = [
        ('batch_id', 'TEXT'),
        ('storage_path', 'TEXT'),
        ('raw_document_ai_json', 'TEXT'),
        ('normalized_json', 'TEXT'),
        ('error_message', 'TEXT'),
        ('file_size', 'INTEGER'),
        ('manually_edited', 'INTEGER DEFAULT 0')
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            cursor.execute(f'ALTER TABLE receipts ADD COLUMN {col_name} {col_type}')
            print(f'✅ Added column: {col_name}')
    
    conn.commit()
    conn.close()
    print('✅ Migration complete!')

if __name__ == '__main__':
    migrate()
