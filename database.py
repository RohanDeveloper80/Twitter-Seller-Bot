cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_data TEXT,
    status TEXT DEFAULT 'available'
)
""")
