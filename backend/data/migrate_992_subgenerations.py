#!/usr/bin/env python3
"""
Reclassify 911 records filed under a bare '992' generation into 992.1 / 992.2.

The shared ladder in app/utils/generations.py used to return "992" for every
2020-and-later 911, but the frontend renders 992 as a *group* of 992.1 and
992.2 (GENERATION_GROUPS in taxonomy.js). A bare '992' therefore has no card of
its own and is excluded from the group's totals, so those records were invisible
on the site. The ladder now returns the sub-generation; this backfills the rows
written before that fix.

Split follows the ladder: the 992.2 facelift arrived for the 2025 model year.

The 911 Race line is deliberately untouched — it uses flat generations, where a
bare '992' is correct.

Usage (from backend/ directory):
    python data/migrate_992_subgenerations.py            # dry run, prints the plan
    python data/migrate_992_subgenerations.py --apply    # writes the changes

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
from app.utils.generations import get_911_generation
from sqlalchemy import select


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(
                AuctionResult.model_line == "911",
                AuctionResult.generation == "992",
            )
        )
        records = result.scalars().all()

        counts: dict[str, int] = {}
        skipped = 0
        for rec in records:
            if rec.year is None:
                skipped += 1
                continue
            target = get_911_generation(rec.year)
            if target == "992":
                # The ladder no longer emits a bare 992; guard against a future
                # edit that reintroduces one rather than writing it back.
                skipped += 1
                continue
            print(f"  #{rec.id}: {rec.year} 992 -> {target} | {(rec.lot_title or '')[:64]}")
            rec.generation = target
            counts[target] = counts.get(target, 0) + 1

        total = sum(counts.values())
        print()
        for gen in sorted(counts):
            print(f"  {gen}: {counts[gen]} record(s)")
        if skipped:
            print(f"  skipped (no year / unresolvable): {skipped}")

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
