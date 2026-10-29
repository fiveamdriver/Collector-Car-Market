#!/usr/bin/env python3
"""
Resolve the 'base' bucket and the other cards-that-don't-exist rows the preflight
lists (~300 sales no page could show).

Rules, from what was agreed card by card:
  * 964 plain -> Carrera 2; 993 and later plain -> Carrera; Targa / Cabriolet /
    Speedster / Turbo / GTS named in the title win (see variants.resolve_911_base).
  * 356 'base' -> the body style in the title (Coupe if none; "Convertible D" is
    a Cabriolet).
  * A handful of one-offs, listed in EXPLICIT with the reason: titles that carry
    a race's year instead of the car's, a pinball machine, a 50th Anniversary
    edition, a one-off 'Sally Special'.

Usage (from backend/ directory):
    python data/migrate_base_bucket.py            # dry run
    python data/migrate_base_bucket.py --apply    # writes the changes

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
from app.utils.variants import cabriolet_variant, parse_356_variant, resolve_911_base
from sqlalchemy import select

# id: (model_line, generation, variant[, year])
EXPLICIT = {
    # Year taken from text about a later event, not the car.
    22815: ("911", "F-Body", "911", 1966),                    # 1966 SWB 911 "sold with ... Le Mans Classic 2022"
    23400: ("911", "G-Body", "Carrera RS 3.0", 1974),         # 1974 RS 3.0 "... Championship winner in 2014"
    # Not production cars / not a Carrera.
    4942:  ("Other", "Other", "base"),                        # a Checkpoint pinball machine
    17730: ("Other", "Other", "base"),                        # 2022 one-off 'Sally Special' ($3.6M charity car)
    17778: ("911 Race", "991", "GT3 Cup"),                    # 911 GT America (the series' Cup car)
    # Special editions and one-offs filed on the wrong card.
    16941: ("911", "991.1", "Carrera S"),                     # 50th Anniversary Edition (Carrera S based)
    16977: ("911", "991.1", "Carrera S"),
    17631: ("911", "991.1", "Carrera S"),
    23220: ("911", "964", "Carrera 2"),                       # Strosek 'Mega Speedster' conversion
    22852: ("911", "964", "Turbo"),                           # "964 TURBO COUPE" (upper-case title)
    23144: ("911", "996.1", "Turbo"),                         # 996 Turbo, not Turbo S
    27901: ("911", "996.2", "GT3 RS"),                        # no 996.1 GT3 RS: the car is a 996.2
    22608: ("911", "992.1", "S/T"),                           # the S/T is a 992.1 car
    27788: ("911", "991.1", "GT3 RS"),                        # "GT3 RS 4.0" is the 991 GT3 RS's engine
    22819: ("911", "991.2", "GT3 RS"),
    20123: ("911", "G-Body", "Carrera RS 3.0"),               # 1975 Carrera RS
    19879: ("Boxster", "986", "S"),                           # Boxster S 550 Spyder Edition
    # 356
    17752: ("356", "356 B", "Coupe"),                         # Carrera Zagato (a coupe, not a Speedster)
    27833: ("356", "356 B", "Coupe"),
    23266: ("356", "356 B", "Roadster"),                      # titled 356B Roadster, filed under 356 A by year
    17927: ("356", "Pre-A", "Coupe"),                         # custom 356 limousine
}


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(AuctionResult.model_line.in_(["911", "356", "Boxster"]))
        )
        plan: Counter = Counter()
        odd = []
        for rec in result.scalars().all():
            title = rec.lot_title or ""
            if rec.id in EXPLICIT:
                tgt = EXPLICIT[rec.id]
                ml, gen, var = tgt[:3]
                year = tgt[3] if len(tgt) > 3 else rec.year
                if (rec.model_line, rec.generation, rec.variant, rec.year) == (ml, gen, var, year):
                    continue
                plan[(f"{rec.model_line}/{rec.generation}/{rec.variant}", f"{ml}/{gen}/{var}")] += 1
                rec.model_line, rec.generation, rec.variant, rec.year = ml, gen, var, year
                continue
            if rec.variant != "base":
                continue
            if rec.model_line == "911":
                var = resolve_911_base(rec.generation, title)
                if var == "base":
                    continue
                var = cabriolet_variant(rec.generation, var, title)
            elif rec.model_line == "356":
                var = parse_356_variant(title)
            else:
                continue
            plan[(f"{rec.model_line}/{rec.generation}/base", f"{rec.model_line}/{rec.generation}/{var}")] += 1
            rec.variant = var

        for (a, b), n in sorted(plan.items(), key=lambda kv: -kv[1]):
            print(f"  {n:3d}  {a}  ->  {b}")
        total = sum(plan.values())
        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
