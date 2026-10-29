#!/usr/bin/env python3
"""
Move 2004-05 "Carrera S" cars from the 996.2 to the 997.1.

The 996 never had a Carrera S, and the 997 launched for MY2005 (Europe 2004), so
the 91 "2005 Porsche 911 Carrera S" lots filed on the 996.2 were 997.1s: the year
ladder (<= 2005 -> 996.2) had no way to tell them apart. get_911_generation now
reads the title; this backfills the rows written before that fix. A stray
'Carrera S' left on the 996 after that (a 1999 "Carrera S" — there is no such car)
is relabelled plain 'Carrera'.

Usage (from backend/ directory):
    python data/migrate_997_boundary.py            # dry run
    python data/migrate_997_boundary.py --apply    # writes the changes

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
from app.utils.generations import get_911_generation
from sqlalchemy import select


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(
                AuctionResult.model_line == "911",
                AuctionResult.generation.in_(["996.1", "996.2"]),
            )
        )
        plan: Counter = Counter()
        for rec in result.scalars().all():
            if rec.year is None:
                continue
            gen = get_911_generation(rec.year, rec.lot_title or "")
            if gen == "997.1":
                plan[(rec.generation, rec.variant, "997.1", rec.variant)] += 1
                rec.generation = "997.1"
            elif rec.variant == "Carrera S":
                plan[(rec.generation, "Carrera S", rec.generation, "Carrera")] += 1
                print(f"    relabel #{rec.id} {rec.year} {rec.lot_title[:60]}")
                rec.variant = "Carrera"

        for (g, v, ng, nv), n in sorted(plan.items(), key=lambda kv: -kv[1]):
            print(f"  {n:3d}  {g}/{v}  ->  {ng}/{nv}")
        total = sum(plan.values())
        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
