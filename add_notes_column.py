import sqlite3

# Connect to the database
conn = sqlite3.connect('receipts.db')
cursor = conn.cursor()

# Check if notes column already exists
cursor.execute("PRAGMA table_info(receipts)")
columns = [col[1] for col in cursor.fetchall()]

if 'notes' not in columns:
    # Add the notes column
    cursor.execute('ALTER TABLE receipts ADD COLUMN notes TEXT')
    conn.commit()
    print("✅ Added 'notes' column to receipts table")
else:
    print("ℹ️ 'notes' column already exists")

conn.close()
