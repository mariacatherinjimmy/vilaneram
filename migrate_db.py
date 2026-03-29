"""
migrate_db.py
Run this ONCE on your existing vilaneram2.db to add new columns.
Usage: python migrate_db.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "vilaneram2.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH} — will be created fresh on first run.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check existing columns
    cur.execute("PRAGMA table_info(users)")
    existing = [row[1] for row in cur.fetchall()]
    print(f"Existing columns: {existing}")

    if "commodities" not in existing:
        cur.execute("ALTER TABLE users ADD COLUMN commodities TEXT")
        print("✓ Added: commodities column")
    else:
        print("- commodities already exists")

    if "shop_address" not in existing:
        cur.execute("ALTER TABLE users ADD COLUMN shop_address VARCHAR(300)")
        print("✓ Added: shop_address column")
    else:
        print("- shop_address already exists")

    conn.commit()
    conn.close()
    print("\nMigration complete!")

if __name__ == "__main__":
    migrate()