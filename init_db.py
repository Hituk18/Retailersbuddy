import sqlite3
def init_db():
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT UNIQUE,
                    quantity INTEGER,
                    cost_price REAL,
                    selling_price REAL,
                    supplier TEXT,
                    expiry_date TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_name TEXT UNIQUE,
                    amount REAL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT,
                    quantity_sold INTEGER,
                    sale_price REAL,
                    date TEXT
                )''')
    conn.commit()
    conn.close()
# Run this once to create tables
init_db()
print("Database initialized successfully!")