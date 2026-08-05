import sqlite3

conn = sqlite3.connect('receipts.db')
cursor = conn.cursor()

# Check existing columns
cursor.execute('PRAGMA table_info(receipts)')
existing_columns = [col[1] for col in cursor.fetchall()]
print('Existing columns:', existing_columns)

# Columns to add
new_columns = [
    ('document_type', 'TEXT DEFAULT "expense"'),
    ('document_number', 'TEXT'),
    ('client_name', 'TEXT'),
    ('client_address', 'TEXT'),
    ('due_date', 'TEXT'),
    ('tax_year', 'TEXT'),
    ('tax_type', 'TEXT'),
    ('payment_method', 'TEXT'),
    ('is_business', 'INTEGER DEFAULT 1'),
    ('is_reimbursable', 'INTEGER DEFAULT 0'),
    ('income_amount', 'REAL DEFAULT 0'),
    ('expense_amount', 'REAL DEFAULT 0'),
    ('tax_amount_paid', 'REAL DEFAULT 0')
]

for col_name, col_type in new_columns:
    if col_name not in existing_columns:
        try:
            cursor.execute(f'ALTER TABLE receipts ADD COLUMN {col_name} {col_type}')
            print(f'Added column: {col_name}')
        except Exception as e:
            print(f'Error adding {col_name}: {e}')
    else:
        print(f'Column already exists: {col_name}')

conn.commit()

# Verify columns now exist
cursor.execute('PRAGMA table_info(receipts)')
columns = [col[1] for col in cursor.fetchall()]
print('Columns after update:', columns)
conn.close()
print('Done!')
