#!/usr/bin/env python3
"""
Move competition cars out of the street model lines.

Street pages were carrying cars that are not street cars — a 964 Carrera Cup
sold as a 'Carrera 2', Clubsport and GT3 R cars on the GT3 / GT2 cards, owner-
built "Track Car"s averaged into the Boxster. Two different fixes:

  1. Factory competition 911s (Carrera Cup, Cup 3.8, GT3 Cup, GT America Cup,
     GT3 R, GT2 R, Clubsport) -> the '911 Race' line, under the flat generation
     and the variant that names the car. Variants the race taxonomy lacked
     (GT3 R, Clubsport, 992 GT2 RS Clubsport) are added in taxonomy.js.
  2. Owner-built "Track Car" / "Race Car" / "Racecar" conversions of road cars
     are NOT moved: they are modified road cars and stay on the card of their
     chassis, like every other modified car (see migrate_modified_to_chassis.py).

Cayman GT4 / GT4 RS Clubsport go to the 'Cayman Race' line (front-page card
'Cayman GT4 Clubsport'). Left alone, and listed in the dry run for review: 924 /
968 Clubsport, Group C / Le Mans / period 'Competition' cars with narrative titles.

Usage (from backend/ directory):
    python data/migrate_race_in_street_lines.py            # dry run
    python data/migrate_race_in_street_lines.py --apply    # writes the changes

Safe to re-run — already-correct records are left untouched.
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
from app.utils.generations import get_911_generation
from sqlalchemy import select

# Lines that are already race lines (or standalone racers) — never touched.
RACE_LINES = {
    '911 Race', '911 GT1', '917', '962', '956', '935', '934', '908', '907',
    '906', '904', '910', '550', 'RS60', '718 RSK', 'RS Spyder',
}

FLAT_GEN = {
    '996.1': '996', '996.2': '996', '997.1': '997', '997.2': '997',
    '991.1': '991', '991.2': '991', '992.1': '992', '992.2': '992',
}

_CARRERA_CUP = re.compile(r'Carrera Cup', re.I)
_CUP_38 = re.compile(r'\bCup 3\.8', re.I)
_GT3_CUP = re.compile(r'GT3 Cup|GT America Cup', re.I)
_GT3_R = re.compile(r'\bGT3 R\b(?!S)', re.I)
_GT2_R = re.compile(r'\bGT2 R\b(?!S)', re.I)
_CLUBSPORT = re.compile(r'Clubsport', re.I)
_GT2_RS_CS = re.compile(r'GT2 RS Clubsport', re.I)
# A tribute / replica / clone of a race car is not a factory race car; it stays
# on the card of the car it was built from (see migrate_rare_variants_genuine.py).
_IMITATION = re.compile(r'Tribute(?! to Carrera RS)|Replica|Re-?creation|Clone|Inspired|-Style', re.I)
# Owner-built conversions. Deliberately excludes "Group C" / "Competition" /
# "Le Mans" narrative titles, which are real period racers needing a human look.
_TRACK_CAR = re.compile(r'Track\s*Car|Race\s*Car|Racecar|Race-Car', re.I)
# A factory race car that happens to be titled "... Race Car".
_FACTORY_WORDS = re.compile(r'Carrera Cup|Cup 3\.8|GT3 Cup|GT America Cup|GT3 R\b|GT2 R\b|Clubsport|\bRSR\b', re.I)


def classify_911_race(rec) -> tuple[str, str] | None:
    """(flat generation, variant) for a factory competition 911, else None."""
    t = rec.lot_title or ""
    if rec.year is None:
        return None
    if _CUP_38.search(t):
        return "993", "Cup 3.8 RSR"
    gen = get_911_generation(rec.year, t)
    gen = FLAT_GEN.get(gen, gen)
    if _GT2_R.search(t):
        return "993", "GT2 R"
    if _CARRERA_CUP.search(t):
        return gen, "Carrera Cup"
    if _GT3_CUP.search(t):
        return gen, "GT3 Cup"
    if _GT3_R.search(t):
        return gen, "GT3 R"
    if _GT2_RS_CS.search(t):
        return gen, "GT2 RS Clubsport"
    if _CLUBSPORT.search(t):
        return gen, "Clubsport"
    return None


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AuctionResult))
        plan: Counter = Counter()
        review = []
        for rec in result.scalars().all():
            line, title = rec.model_line, rec.lot_title or ""
            if not line or line in RACE_LINES or line.endswith(" Race") or rec.variant == "Modified":
                continue

            if line == "911" and not _IMITATION.search(title):
                target = classify_911_race(rec)
                if target:
                    gen, var = target
                    plan[(f"911/{rec.generation}/{rec.variant}", f"911 Race/{gen}/{var}")] += 1
                    rec.model_line, rec.generation, rec.variant = "911 Race", gen, var
                    continue

            if line == "Cayman" and _CLUBSPORT.search(title) and not _IMITATION.search(title):
                # Cayman GT4 / GT4 RS Clubsport: factory race cars with their own
                # front-page card ('cayman-gt4-clubsport' -> model line 'Cayman Race').
                plan[(f"Cayman/{rec.generation}/{rec.variant}", "Cayman Race/Cayman Race/base")] += 1
                rec.model_line, rec.generation, rec.variant = "Cayman Race", "Cayman Race", "base"
                continue

            if _CLUBSPORT.search(title) and line != "911":
                review.append(rec)   # 924 / 968 Clubsport: no race card yet
                continue


        total = sum(plan.values())
        for (a, b), n in sorted(plan.items(), key=lambda kv: -kv[1]):
            print(f"  {n:3d}  {a}  ->  {b}")
        print(f"\n  left for review (factory Clubsport on a line with no race card): {len(review)}")
        for rec in review[:6]:
            print(f"    #{rec.id} {rec.model_line}/{rec.generation} {rec.lot_title[:70]}")

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
