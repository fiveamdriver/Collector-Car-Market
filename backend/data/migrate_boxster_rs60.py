#!/usr/bin/env python3
"""
Move the 2008 Boxster RS 60 Spyder into its own 'RS 60 Spyder' variant on the
987.1 Boxster.

The ingests filed these under the generic 'Spyder' (or 'Spyder RS') pattern. On
the 987.1 that variant has no card, and moving them to the 987.2 Spyder would be
wrong: the RS 60 is a 2008 limited edition (1,960 built), a different car from
the 2011-12 Boxster Spyder. The ingests now classify them correctly; this
backfills the existing rows.

Usage (from backend/ directory):
    python data/migrate_boxster_rs60.py            # dry run, prints the plan
    python data/migrate_boxster_rs60.py --apply    # writes the changes

Safe to re-run — already-correct records are left untouched.
"""
import asyncio
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from app.utils.variants import is_boxster_rs60
from sqlalchemy import select


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(AuctionResult.model_line == "Boxster")
        )
        changed = 0
        for rec in result.scalars().all():
            if not rec.lot_title or not is_boxster_rs60(rec.lot_title):
                continue
            if rec.generation == "987.1" and rec.variant == "RS 60 Spyder":
                continue
            print(f"  #{rec.id}: {rec.generation}/{rec.variant} -> 987.1/RS 60 Spyder | {rec.lot_title[:60]}")
            rec.generation = "987.1"
            rec.variant = "RS 60 Spyder"
            changed += 1

        if apply:
            await session.commit()
            print(f"\nUpdated {changed} record(s).")
        else:
            print(f"\nDRY RUN — {changed} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
