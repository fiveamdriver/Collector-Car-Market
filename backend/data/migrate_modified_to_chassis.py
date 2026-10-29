#!/usr/bin/env python3
"""
Dissolve the hidden 'Modified' variant: file every modified car under the
generation and variant of its chassis.

A backdate, tribute, engine swap or owner-built track car is still a specific
car underneath — a "Backdated 1987 Porsche 911 Carrera" is a 1987 chassis, so it
belongs in G-Body / Carrera 3.2, and a "4.0L-Powered 2010 911 GT3 RS" on the
997.2 GT3 RS card. The earlier cleanups parked them under 'Modified', a variant
no card shows, so ~540 sales were invisible. This re-derives generation and
variant from the model year and title with the same parsers the ingest scripts
use (Gooding's, which share the matchers in app/utils/).

Coachbuilders (Singer, Gunther Werks, Emory) are not here: they have their own
model lines and were never 'Modified'.

Usage (from backend/ directory):
    python data/migrate_modified_to_chassis.py            # dry run
    python data/migrate_modified_to_chassis.py --apply    # writes the changes

Safe to re-run — only rows still marked 'Modified' are touched.
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
from data.gooding_ingest import parse_generation, parse_variant
from sqlalchemy import select

# Standalone models have no generation or variant cards; the row just needs a
# non-'Modified' variant so it counts toward the model page.
STANDALONE = {"550", "912"}


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(AuctionResult.variant == "Modified")
        )
        plan: Counter = Counter()
        for rec in result.scalars().all():
            line, title = rec.model_line, rec.lot_title or ""
            if line in STANDALONE:
                gen, var = rec.generation, "base"
            else:
                gen = parse_generation(line, rec.year, title)
                var = parse_variant(line, rec.year, title)
            plan[(line, rec.generation, gen, var)] += 1
            rec.generation, rec.variant = gen, var

        total = sum(plan.values())
        by_target: Counter = Counter()
        for (line, old_gen, gen, var), n in plan.items():
            by_target[(line, gen, var)] += n
        for (line, gen, var), n in sorted(by_target.items(), key=lambda kv: (kv[0][0], kv[0][1], -kv[1])):
            print(f"  {n:3d}  {line} / {gen} / {var}")
        moved_gen = sum(n for (l, og, g, v), n in plan.items() if og != g)
        print(f"\n  changed generation as well as variant: {moved_gen}")

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
