"""
Run this BEFORE demoing the app to a NEW/different shop.

It safely archives the current shop's database (doesn't delete it — just
renames it with a timestamp, so you can keep it for your project report)
and resets the app to a blank slate. The next person who signs up becomes
the new shop's owner and gets asked for the new shop name, exactly like a
true first-time setup.

Usage:
    python reset_for_new_shop.py

You do NOT need to run this between normal logins/testing for the SAME
shop — only when you're about to demo to a genuinely different shop and
want a clean "Welcome! Let's set up your shop" screen for them.
"""
import os
import shutil
from datetime import datetime

DB_PATH = os.path.join("instance", "shop.db")


def main():
    if not os.path.exists(DB_PATH):
        print("No existing database found — this is already a fresh install.")
        print("Just run 'python run.py' and sign up as the new shop's owner.")
        return

    print("This will archive the CURRENT shop's data (products, bills, expenses,")
    print("accounts) and start fresh so the next signup becomes a new shop's owner.")
    print("Nothing is deleted — your current data is kept as a backup file.\n")
    confirm = input("Type YES to continue: ")

    if confirm.strip().upper() != "YES":
        print("Cancelled. Nothing changed.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"shop_backup_{timestamp}.db"
    archive_path = os.path.join("instance", archive_name)
    shutil.move(DB_PATH, archive_path)

    print(f"\nDone. Previous shop's data archived to: instance/{archive_name}")
    print("Now run 'python run.py' and sign up as the new shop's owner —")
    print("you'll see the shop name field again, like a true first-time setup.")


if __name__ == "__main__":
    main()
