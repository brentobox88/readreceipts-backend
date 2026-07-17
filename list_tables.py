import sqlite3

conn = sqlite3.connect('receipts.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=== TABLES IN DATABASE ===")
if tables:
    for table in tables:
        print(f"  - {table[0]}")
else:
    print("  No tables found!")

# Also check if 'receipts' table exists specifically
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='receipts'")
receipts_table = cursor.fetchone()
if receipts_table:
    print("\n✅ 'receipts' table exists!")
    
    # Show its columns
    cursor.execute("PRAGMA table_info(receipts)")
    columns = cursor.fetchall()
    print("\nColumns in 'receipts' table:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
else:
    print("\n❌ 'receipts' table does NOT exist!")

conn.close()
