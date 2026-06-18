import sqlite3

def create_database():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    # Orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        user_id TEXT,
        amount INTEGER,
        utr TEXT,
        status TEXT
    )
    """)

    # Inventory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_data TEXT,
        status TEXT DEFAULT 'available'
    )
    """)

    conn.commit()
    conn.close()

    print("Database Ready")

create_database()
