#!/usr/bin/env python3
"""
Add auction_results.original_price / original_currency (schema only, no data).

    python data/migrate_add_original_price.py           # dry run: print the SQL
    python data/migrate_add_original_price.py --apply   # run it

Idempotent (ADD COLUMN IF NOT EXISTS). Both columns are nullable and start
NULL; data/backfill_original_price.py fills them for RM Sotheby's and Bonhams.
Undo: ALTER TABLE auction_results DROP COLUMN original_price, DROP COLUMN original_currency;
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

SQL = (
    "ALTER TABLE auction_results "
    "ADD COLUMN IF NOT EXISTS original_price INTEGER, "
    "ADD COLUMN IF NOT EXISTS original_currency TEXT"
)


async def main(apply: bool) -> None:
    async with engine.begin() as conn:
        cols = {r[0] for r in (await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'auction_results'"))).all()}
        missing = [c for c in ("original_price", "original_currency") if c not in cols]
        print(f"Missing columns: {missing or 'none'}")
        print(f"SQL: {SQL}")
        if apply and missing:
            await conn.execute(text(SQL))
            print("Applied.")
        elif not apply:
            print("Dry run: nothing changed. Re-run with --apply.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
