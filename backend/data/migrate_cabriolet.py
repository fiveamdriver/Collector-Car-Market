#!/usr/bin/env python3
"""
Give each 911 generation a single Cabriolet card (rear- and all-wheel-drive
together) and take the cabriolets out of the Carrera 2 / Carrera 4 / Carrera S
cards.

Only Carrera-family trims move (see app.utils.variants.cabriolet_variant);
Turbo, Speedster and GT cars keep their own cards, and Targas keep theirs.

Usage (from backend/ directory):
    python data/migrate_cabriolet.py            # dry run
    python data/migrate_cabriolet.py --apply    # writes the changes

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
from app.utils.variants import cabriolet_variant
from sqlalchemy import select


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(AuctionResult.model_line == "911")
        )
        plan: Counter = Counter()
        per_gen: Counter = Counter()
        sample = []
        for rec in result.scalars().all():
            new = cabriolet_variant(rec.generation, rec.variant, rec.lot_title or "")
            if new == rec.variant:
                continue
            plan[(rec.generation, rec.variant)] += 1
            per_gen[rec.generation] += 1
            if len(sample) < 14:
                sample.append(f"    #{rec.id} {rec.generation}/{rec.variant}  {rec.lot_title[:70]}")
            rec.variant = new

        for (gen, var), n in sorted(plan.items()):
            print(f"  {gen:7s} {var:12s} -> Cabriolet: {n}")
        print()
        for gen, n in per_gen.items():
            print(f"  {gen}: {n}")
        print()
        print("\n".join(sample))

        total = sum(plan.values())
        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
