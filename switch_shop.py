"""
Lists every shop you've ever set up on this PC (the currently active one,
plus any archived by reset_for_new_shop.py), and lets you switch which one
is active — without losing any of them. Useful if you're demoing multiple
shops and need to log in as a different one than what's currently active.

Usage:
    python switch_shop.py
"""
import os
import sqlite3
import shutil
from datetime import datetime

INSTANCE_DIR = "instance"
ACTIVE_DB = os.path.join(INSTANCE_DIR, "shop.db")


def get_shop_name(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'shop_name'")
        row = cur.fetchone()
        conn.close()
        return row[0] if row else "(unnamed shop)"
    except Exception:
        return "(could not read this file)"


def main():
    if not os.path.isdir(INSTANCE_DIR):
        print("No 'instance' folder found yet — nothing to switch between.")
        return

    entries = []  # (label, file_path)

    if os.path.exists(ACTIVE_DB):
        name = get_shop_name(ACTIVE_DB)
        entries.append((f"{name}  [CURRENTLY ACTIVE]", ACTIVE_DB))

    backups = sorted(
        f for f in os.listdir(INSTANCE_DIR)
        if f.startswith("shop_backup_") and f.endswith(".db")
    )
    for b in backups:
        path = os.path.join(INSTANCE_DIR, b)
        name = get_shop_name(path)
        entries.append((f"{name}  (archived: {b})", path))

    if not entries:
        print("No shops found yet. Run the app and sign up to create one.")
        return

    print("Shops found on this PC:\n")
    for i, (label, _) in enumerate(entries, 1):
        print(f"  {i}. {label}")

    choice = input("\nType the number of the shop to make ACTIVE (Enter to cancel): ").strip()
    if not choice:
        print("Cancelled. Nothing changed.")
        return

    try:
        idx = int(choice) - 1
        label, target_path = entries[idx]
    except (ValueError, IndexError):
        print("Invalid choice.")
        return

    if target_path == ACTIVE_DB:
        print("That shop is already active — nothing to do.")
        return

    if os.path.exists(ACTIVE_DB):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = os.path.join(INSTANCE_DIR, f"shop_backup_{timestamp}.db")
        shutil.move(ACTIVE_DB, archive_path)
        print(f"Archived the previously active shop to: {archive_path}")

    # COPY (not move) so the backup file still exists — you can switch
    # back to it again later without losing anything.
    shutil.copy(target_path, ACTIVE_DB)
    print(f"\nDone. '{label.split('  [')[0].split('  (')[0]}' is now the active shop.")
    print("Run 'python run.py' (or your usual launcher) to use it.")


if __name__ == "__main__":
    main()
