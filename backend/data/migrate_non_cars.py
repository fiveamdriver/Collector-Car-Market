#!/usr/bin/env python3
"""
Move engines, parts and memorabilia out of the car cards.

Lots such as "1974 Porsche 911 Carrera Type 911/83 2.7L MFI Engine" were parsed
as cars, so a $40,000 engine sat on the Carrera 2.7 MFI card among the $200k+
cars, alongside transaxles, seats, a carbon dashboard and a body kit. They go to
model line 'Other', which no page shows (the same place earlier cleanups put
tractors and manuals). See app.utils.variants.is_not_a_car for what counts.

Usage (from backend/ directory):
    python data/migrate_non_cars.py            # dry run
    python data/migrate_non_cars.py --apply    # writes the changes

Safe to re-run.
"""
import asyncio
import os
import sys
from collections import Counter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from app.utils.variants import is_not_a_car
from sqlalchemy import select


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(AuctionResult.model_line != "Other")
        )
        plan: Counter = Counter()
        rows = []
        for rec in result.scalars().all():
            if not is_not_a_car(rec.lot_title):
                continue
            plan[(rec.model_line, rec.generation, rec.variant)] += 1
            rows.append(rec)
            rec.model_line, rec.generation, rec.variant = "Other", "Other", "base"

        for (line, gen, var), n in sorted(plan.items(), key=lambda kv: -kv[1]):
            print(f"  {n:3d}  {line} / {gen} / {var}")
        print()
        for rec in rows:
            print(f"    #{rec.id} ${rec.sold_price}  {rec.lot_title[:85]}")

        total = len(rows)
        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
