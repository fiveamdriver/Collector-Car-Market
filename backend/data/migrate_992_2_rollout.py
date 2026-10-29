#!/usr/bin/env python3
"""
Move 2025 cars that are still 992.1 off the 992.2 card.

The ladder in app/utils/generations.py split the 992 at MY2025 for every model,
but the facelift rolled out model by model. A 2025 GT3 RS, Turbo S or Turbo
50 Years is a 992.1 — the 992.2 Turbo S arrived as a 2026 model and no 992.2
GT3 RS has been delivered — so 26 such cars sat on 992.2. The ladder now
checks the title for 2025 cars; this re-derives the stored rows the same way.

Usage (from backend/ directory):
    python data/migrate_992_2_rollout.py            # dry run
    python data/migrate_992_2_rollout.py --apply    # writes the changes

Safe to re-run.
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
                AuctionResult.generation.in_(("992.1", "992.2")),
            )
        )
        changed = 0
        for rec in result.scalars().all():
            target = get_911_generation(rec.year, rec.lot_title or "")
            if target == rec.generation:
                continue
            print(f"  #{rec.id}: {rec.year} {rec.variant:<10} {rec.generation} -> {target} | {(rec.lot_title or '')[:60]}")
            rec.generation = target
            changed += 1

        if apply:
            await session.commit()
            print(f"\nUpdated {changed} record(s).")
        else:
            print(f"\nDRY RUN — {changed} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
