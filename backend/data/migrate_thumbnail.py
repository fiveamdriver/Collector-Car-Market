#!/usr/bin/env python3
"""
Migration: rename color → thumbnail_url in auction_results.

Usage (from backend/ directory):
    python data/migrate_thumbnail.py
"""
import os
import sqlite3

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH     = os.path.join(BACKEND_DIR, "pcarmarket.db")


def get_columns(cursor, table: str) -> list[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cols = get_columns(cur, "auction_results")

    if "color" in cols and "thumbnail_url" not in cols:
        cur.execute("ALTER TABLE auction_results RENAME COLUMN color TO thumbnail_url")
        conn.commit()
        print("Renamed column: color → thumbnail_url")
    elif "thumbnail_url" not in cols:
        cur.execute("ALTER TABLE auction_results ADD COLUMN thumbnail_url TEXT")
        conn.commit()
        print("Added column: thumbnail_url")
    else:
        print("Column thumbnail_url already exists — nothing to do.")

    if "color" in cols and "thumbnail_url" in get_columns(cur, "auction_results"):
        # If old column still exists after rename (shouldn't happen, but guard)
        pass

    conn.close()
    print(f"Done. Database: {DB_PATH}")


if __name__ == "__main__":
    main()
