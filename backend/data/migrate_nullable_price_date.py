#!/usr/bin/env python3
"""
Make sold_price and sold_date nullable in auction_results.

SQLite doesn't support ALTER COLUMN, so we recreate the table.
Safe to re-run — checks if migration is already applied before proceeding.

Usage (from backend/ directory):
    python data/migrate_nullable_price_date.py
"""
import sqlite3
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.config import DATABASE_PATH


def main() -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(auction_results)")
    cols = {row[1]: row for row in cur.fetchall()}

    price_notnull = cols["sold_price"][3]  # 1 = NOT NULL
    date_notnull  = cols["sold_date"][3]

    if not price_notnull and not date_notnull:
        print("Already nullable — nothing to do.")
        conn.close()
        return

    print("Recreating auction_results with nullable sold_price / sold_date ...")

    cur.executescript("""
        BEGIN;

        CREATE TABLE auction_results_new (
            id               INTEGER NOT NULL PRIMARY KEY,
            make             VARCHAR NOT NULL,
            model_line       VARCHAR NOT NULL,
            generation       VARCHAR NOT NULL,
            variant          VARCHAR NOT NULL,
            year             INTEGER NOT NULL,
            transmission     VARCHAR NOT NULL,
            is_widebody      BOOLEAN,
            mileage          INTEGER,
            thumbnail_url    VARCHAR,
            sold_price       INTEGER,
            auction_source   VARCHAR NOT NULL,
            auction_url      VARCHAR,
            sold_date        DATE,
            lot_title        VARCHAR,
            exterior_color   TEXT,
            paint_to_sample  BOOLEAN,
            production_number VARCHAR,
            created_at       DATETIME NOT NULL
        );

        INSERT INTO auction_results_new
            SELECT id, make, model_line, generation, variant, year,
                   transmission, is_widebody, mileage, thumbnail_url,
                   sold_price, auction_source, auction_url, sold_date,
                   lot_title, exterior_color, paint_to_sample,
                   production_number, created_at
            FROM auction_results;

        DROP TABLE auction_results;
        ALTER TABLE auction_results_new RENAME TO auction_results;

        CREATE INDEX IF NOT EXISTS ix_auction_results_model_line  ON auction_results (model_line);
        CREATE INDEX IF NOT EXISTS ix_auction_results_generation  ON auction_results (generation);
        CREATE INDEX IF NOT EXISTS ix_auction_results_variant     ON auction_results (variant);
        CREATE INDEX IF NOT EXISTS ix_auction_results_sold_date   ON auction_results (sold_date);

        COMMIT;
    """)

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
