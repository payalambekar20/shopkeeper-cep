"""
Prints a clean, readable summary of everything currently stored in the
database — users, products, bills, expenses, settings. No extra tools or
installs needed (uses Python's built-in sqlite3 module), so this is a good
thing to run live during a demo to actually SHOW the database contents
instead of just claiming data is being stored.

Usage:
    python view_database.py
"""
import sqlite3
import os

DB_PATH = os.path.join("instance", "shop.db")


def line(char="-", length=70):
    print(char * length)


def show_table(conn, title, query, headers):
    print(f"\n{title}")
    line()
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    if not rows:
        print("  (no rows yet)")
        return
    print("  " + " | ".join(headers))
    line()
    for row in rows:
        print("  " + " | ".join(str(v) for v in row))
    print(f"  ({len(rows)} row(s))")


def main():
    if not os.path.exists(DB_PATH):
        print(f"No database found at {DB_PATH} yet. Run the app and sign up first.")
        return

    conn = sqlite3.connect(DB_PATH)

    print("=" * 70)
    print("  SHOPKEEPER DATABASE CONTENTS")
    print("=" * 70)

    # Secret key is masked, even for your own viewing — it should never be
    # displayed or shared, since it's what keeps login sessions secure.
    show_table(
        conn, "SETTINGS (shop name, etc.)",
        "SELECT key, CASE WHEN key = 'app_secret_key' THEN '(hidden for security)' ELSE value END FROM settings",
        ["key", "value"],
    )

    show_table(
        conn, "USERS (logins)",
        "SELECT id, username, role, created_at FROM users",
        ["id", "username", "role", "created_at"],
    )

    show_table(
        conn, "PRODUCTS",
        "SELECT id, name, category, unit FROM products",
        ["id", "name", "category", "unit"],
    )

    show_table(
        conn, "PRODUCT VARIANTS (sizes/prices/stock)",
        "SELECT id, product_id, label, price, stock_qty FROM product_variants",
        ["id", "product_id", "label", "price", "stock_qty"],
    )

    show_table(
        conn, "BILLS",
        "SELECT id, bill_number, customer_name, total, created_at FROM bills",
        ["id", "bill_number", "customer_name", "total", "created_at"],
    )

    show_table(
        conn, "BILL ITEMS",
        "SELECT id, bill_id, product_name, unit_price, quantity, line_total FROM bill_items",
        ["id", "bill_id", "product_name", "unit_price", "quantity", "line_total"],
    )

    show_table(
        conn, "EXPENSES",
        "SELECT id, description, category, amount, expense_date FROM expenses",
        ["id", "description", "category", "amount", "expense_date"],
    )

    conn.close()
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
