import sqlite3

DB_NAME = "bot.db"


def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_data TEXT,
        status TEXT DEFAULT 'available'
    )
    """)

    conn.commit()
    conn.close()


def add_account(account_data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO inventory (account_data, status) VALUES (?, ?)",
        (account_data, "available")
    )

    conn.commit()
    conn.close()


def get_stock():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM inventory WHERE status='available'"
    )

    stock = cursor.fetchone()[0]

    conn.close()

    return stock


def get_accounts(qty):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, account_data FROM inventory WHERE status='available' LIMIT ?",
        (qty,)
    )

    rows = cursor.fetchall()

    if len(rows) < qty:
        conn.close()
        return None

    ids = [str(row[0]) for row in rows]
    accounts = [row[1] for row in rows]

    cursor.execute(
        f"UPDATE inventory SET status='sold' WHERE id IN ({','.join(ids)})"
    )

    conn.commit()
    conn.close()

    return accounts


create_database()
