#!/usr/bin/env python3
"""
Add auction_results.details_text, details_fetched_at and details_filled.

Both are nullable, so existing reads and ingest scripts are unaffected. They are
filled by data/enrich_details.py.

Usage (from backend/ directory):
    python data/migrate_details_columns.py

Safe to re-run.
"""
import asyncio
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.database import engine
from sqlalchemy import text


async def main() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS details_text TEXT"))
        await conn.execute(text(
            "ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS details_fetched_at TIMESTAMP"))
        await conn.execute(text(
            "ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS details_filled TEXT"))
    await engine.dispose()
    print("auction_results: details_text, details_fetched_at, details_filled present.")


if __name__ == "__main__":
    asyncio.run(main())
