#!/usr/bin/env python3
"""
Re-file 911s whose generation the year ladder got wrong at a facelift boundary.

get_911_generation now reads the title for the models that changed generation
in a different model year to the Carrera (2009 Turbo / GT2 -> 997.1, 2013 Turbo
-> 997.2, ...) and honours a chassis named in the title ("Type 996", "991.2").
This re-runs it over every street 911 and moves the rows it now files
differently. A variant that has no card in the new generation is mapped to its
equivalent (964 "Carrera 2" -> 993 "Carrera"); a move with no equivalent is
reported and skipped, never forced.

Usage (from backend/):
    python data/migrate_facelift_boundaries.py            # dry run, lists every move
    python data/migrate_facelift_boundaries.py --apply    # writes them

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
import re

# "2000-Mile 2006 Porsche 911 Cabriolet" was stored as a 2000.
_MILEAGE_YEAR = re.compile(r"^\s*(?:19|20)\d{2}-(?:Mile|Kilometer|km)\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(19|20)\d{2}\b(?!-(?:Mile|Kilometer|km)\b)", re.IGNORECASE)
_VIN_TEXT = re.compile(r"\bWP[0O][A-HJ-NPR-Z0-9]{14}\b")
# "Carrera 40th Anniversary" was matched as "Carrera 4".
_C40 = re.compile(r"Carrera\s+40th", re.IGNORECASE)

from app.utils.cards_911 import target_variant  # noqa: E402


async def main() -> None:
    apply = "--apply" in sys.argv
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(AuctionResult).where(AuctionResult.model_line == "911",
                                        AuctionResult.year.isnot(None))
        )).scalars().all()
        plan: Counter = Counter()
        skipped = []
        for rec in rows:
            title = rec.lot_title or ""
            if _MILEAGE_YEAR.search(title):
                m = _YEAR.search(title)
                if m and int(m.group()) != rec.year:
                    print(f"  #{rec.id:<6} year {rec.year} -> {m.group()}   {title[:70]}")
                    rec.year = int(m.group())
                    plan[("year", "", "", "")] += 1
            if rec.variant == "Carrera 4" and re.search(r"Carrera\s*4\s*GTS\b", title):
                print(f"  #{rec.id:<6} variant Carrera 4 -> Carrera GTS   {title[:70]}")
                rec.variant = "Carrera GTS"
                plan[("variant", "Carrera 4", "", "Carrera GTS")] += 1
            if rec.variant == "Carrera 4" and _C40.search(title):
                print(f"  #{rec.id:<6} variant Carrera 4 -> Carrera   {title[:70]}")
                rec.variant = "Carrera"
                plan[("variant", "Carrera 4", "", "Carrera")] += 1
            vin = rec.chassis
            if not (vin and len(vin) == 17):
                hit = _VIN_TEXT.search(rec.details_text or "")
                vin = hit.group() if hit else None
            new_gen = get_911_generation(rec.year, title, vin)
            if new_gen == rec.generation:
                continue
            new_var = target_variant(rec.variant, new_gen)
            if new_var is None:
                skipped.append((rec.id, rec.year, rec.generation, rec.variant, new_gen, rec.lot_title))
                continue
            plan[(rec.generation, rec.variant, new_gen, new_var)] += 1
            print(f"  #{rec.id:<6} {rec.year} {rec.auction_source:<18} {rec.generation}/{rec.variant}"
                  f" -> {new_gen}/{new_var}   {(rec.lot_title or '')[:70]}")
            rec.generation, rec.variant = new_gen, new_var

        print("\nSummary:")
        for (g, v, ng, nv), n in sorted(plan.items(), key=lambda kv: -kv[1]):
            print(f"  {n:4d}  {g}/{v}  ->  {ng}/{nv}")
        for s in skipped:
            print(f"  SKIPPED (no card for variant in target): {s}")
        total = sum(plan.values())
        if apply:
            await session.commit()
            print(f"\nApplied {total} moves.")
        else:
            print(f"\nDry run: {total} moves. Re-run with --apply to write them.")


if __name__ == "__main__":
    asyncio.run(main())
