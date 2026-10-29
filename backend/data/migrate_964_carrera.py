#!/usr/bin/env python3
"""
Split the 964's generic 'Carrera' into Carrera 2 and Carrera 4, and file the
1989 Carrera 4s that the year ladder put under G-Body onto the 964.

The 964 was sold as the rear-drive Carrera 2 and the all-wheel-drive Carrera 4,
so the site shows those two cards and no plain "Carrera". The 964 'base' bucket
is resolved the same way, except that titles naming a specific car (Targa,
Speedster, America, Turbo) go to that variant instead.

Usage (from backend/ directory):
    python data/migrate_964_carrera.py            # dry run, prints the plan
    python data/migrate_964_carrera.py --apply    # writes the changes

Safe to re-run — already-correct records are left untouched.
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
from app.utils.variants import fix_964_carrera, is_early_carrera_4, _C4, _C2
from sqlalchemy import select


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(
                AuctionResult.model_line == "911",
                AuctionResult.generation.in_(["964", "G-Body"]),
            )
        )
        plan: Counter = Counter()
        defaulted = []
        for rec in result.scalars().all():
            title = rec.lot_title or ""
            gen, var = rec.generation, rec.variant

            if gen == "G-Body":
                # Only the 1989 Carrera 4s move; the rest of G-Body is untouched.
                if rec.year is None or var == "Modified" or not is_early_carrera_4(rec.year, title):
                    continue
                new_gen, new_var = "964", "Carrera 4"
            else:
                new_gen, new_var = "964", fix_964_carrera(var, title)

            if (gen, var) == (new_gen, new_var):
                continue
            plan[(gen, var, new_gen, new_var)] += 1
            # A generic title with no drive marker defaults to Carrera 2.
            if new_var == "Carrera 2" and not _C2.search(title) and not _C4.search(title):
                defaulted.append(rec)
            rec.generation, rec.variant = new_gen, new_var

        total = sum(plan.values())
        for (g, v, ng, nv), n in sorted(plan.items()):
            print(f"  {g}/{v} -> {ng}/{nv}: {n}")
        print(f"\n  defaulted to Carrera 2 (title says neither 2 nor 4): {len(defaulted)}")
        for rec in defaulted[:8]:
            print(f"    #{rec.id} {rec.lot_title[:70]}")

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
