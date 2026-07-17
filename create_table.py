import sqlite3
from datetime import datetime

conn = sqlite3.connect('receipts.db')
cursor = conn.cursor()

# Create the receipts table with your full schema
cursor.execute('''
CREATE TABLE IF NOT EXISTS receipts (
    id TEXT PRIMARY KEY,
    merchant_name TEXT,
    merchant_address TEXT,
    transaction_date TEXT,
    receipt_number TEXT,
    subtotal REAL,
    tax_amount REAL,
    tax_rate REAL,
    total_amount REAL,
    currency TEXT,
    filename TEXT,
    file_path TEXT,
    file_size INTEGER,
    image_url TEXT,
    raw_text TEXT,
    parsed_data TEXT,
    confidence_score REAL,
    business TEXT,
    category TEXT,
    tags TEXT,
    notes TEXT,
    line_items TEXT,
    status TEXT,
    manually_edited INTEGER,
    is_exported INTEGER,
    created_at TEXT,
    updated_at TEXT,
    processed_at TEXT
)
''')

conn.commit()
print("✅ Receipts table created successfully!")

# Verify the table was created
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"📊 Tables in database: {[t[0] for t in tables]}")

# Show the columns
cursor.execute("PRAGMA table_info(receipts)")
columns = cursor.fetchall()
print("\n📋 Columns in receipts table:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
