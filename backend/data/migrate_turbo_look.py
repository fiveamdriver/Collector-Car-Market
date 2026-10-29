#!/usr/bin/env python3
"""
Take Turbo-Look and turbo-swapped cars off the Turbo cards.

The variant matchers read the word "Turbo" in a title, so a Carrera 3.2 with the
factory M491 "Turbo-Look" package, a 911SC with a turbo engine swap, and a 964
Carrera 2 "Turbo Look" were all filed as Turbos and averaged into cards of real
Turbos. They go to the card of the car they actually are (Carrera 3.2, SC,
Carrera 2, Speedster...), by model year. Titles are not altered — M491 and
"Turbo-Look" stay in the displayed name.

The test is conservative: a row only moves if, with the impostor phrases removed
(app.utils.variants.strip_turbo_impostor), its title no longer says Turbo or 930
at all. "Turbo Special Wishes" and "3.3 Turbo Coupe" stay put.

Usage (from backend/ directory):
    python data/migrate_turbo_look.py            # dry run
    python data/migrate_turbo_look.py --apply    # writes the changes

Safe to re-run.
"""
import asyncio
import os
import re
import sys
from collections import Counter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from app.utils.variants import strip_turbo_impostor
from data.gooding_ingest import parse_generation, parse_variant
from sqlalchemy import select

TURBO_CARDS = ("930 Turbo", "Turbo", "Turbo S")


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(
                AuctionResult.model_line == "911",
                AuctionResult.variant.in_(TURBO_CARDS),
            )
        )
        plan: Counter = Counter()
        sample = []
        for rec in result.scalars().all():
            title = rec.lot_title or ""
            cleaned = strip_turbo_impostor(title)
            if cleaned == title or re.search(r"Turbo|\b930\b", cleaned, re.IGNORECASE):
                continue
            gen = parse_generation("911", rec.year, title)
            var = parse_variant("911", rec.year, title)
            if (gen, var) == (rec.generation, rec.variant):
                continue
            plan[(f"{rec.generation}/{rec.variant}", f"{gen}/{var}")] += 1
            sample.append(f"    #{rec.id} {rec.year} ${rec.sold_price}  {title[:62]}  ->  {gen}/{var}")
            rec.generation, rec.variant = gen, var

        total = sum(plan.values())
        for (a, b), n in sorted(plan.items(), key=lambda kv: -kv[1]):
            print(f"  {n:3d}  {a}  ->  {b}")
        print()
        print("\n".join(sample[:12]))

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
