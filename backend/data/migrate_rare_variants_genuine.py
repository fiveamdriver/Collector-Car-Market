#!/usr/bin/env python3
"""
Keep rare-variant cards to genuine cars.

A rare card — Carrera RS 2.7, 993 GT2, Slant Nose, RS America — is only
meaningful if it holds the real thing. Replicas, recreations, tributes,
conversions and clones carry the rare name in their titles but are built on an
ordinary donor, and averaging them in drags a seven-figure card down to a few
hundred thousand (or a Slant Nose conversion of a $30k SC into a "Flachbau").

Those cars stay in the database and on the site; they move to the card of the
car they were built from ("Slant Nose Conversion" of an SC -> SC, a "993 Turbo
GT2 Tribute" -> 993 Turbo). The donor is read from the title with the rare
name stripped out. Non-cars (a "Carrera RS Tool Kit") go to model line 'Other'.

Genuine cars with a modified-sounding title are left alone: the factory
"Tribute to Carrera RS Package" on the 992 GT3 RS, a GT2 sold as a track car.

Usage (from backend/ directory):
    python data/migrate_rare_variants_genuine.py            # dry run
    python data/migrate_rare_variants_genuine.py --apply    # writes the changes

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
from data.gooding_ingest import parse_generation, parse_variant
from sqlalchemy import select

# (generation, variant) cards that must hold only genuine cars.
RARE = {
    ("F-Body", "Carrera RS 2.7"), ("F-Body", "S/T"), ("F-Body", "911R"),
    ("G-Body", "Turbo 3.3 Slant Nose"), ("G-Body", "Carrera RS 3.0"),
    ("964", "Carrera RS"), ("964", "RS 3.8"), ("964", "RS America"), ("964", "Turbo S"),
    ("993", "Carrera RS"), ("993", "GT2"), ("993", "Turbo S"),
    ("996.1", "GT2"), ("996.2", "GT2"), ("996.1", "GT3 RS"), ("996.2", "GT3 RS"),
    ("997.1", "GT2"), ("997.1", "GT3 RS"), ("997.2", "GT2 RS"), ("997.2", "GT3 RS"),
    ("997.2", "GT3 RS 4.0"), ("997.2", "Sport Classic"),
    ("991.1", "R"), ("991.1", "GT3 RS"), ("991.2", "GT2 RS"), ("991.2", "GT3 RS"),
    ("992.1", "S/T"), ("992.1", "Dakar"), ("992.1", "Sport Classic"),
    ("992.1", "GT3 RS"), ("992.2", "GT3 RS"),
    ("G-Body", "Speedster"), ("964", "Speedster"), ("993", "Speedster"),
    ("997.2", "Speedster"), ("991.2", "Speedster"),
}

# Replicas / non-cars on standalone cards and race lines, which have no donor
# card to fall back on by title. Reviewed by hand.
EXPLICIT = {
    19985: ("Other", "Other", "base"),     # 917 Laser Replica
    18163: ("Other", "Other", "base"),     # 550 Spyder Beck Re-creation
    26462: ("Other", "Other", "base"),     # Carrera GT promo kit + media pack
    17287: ("968", "968", "base"),         # 968 Turbo S Clone (was on 968 Race)
    18203: ("911", "G-Body", "SC"),        # 911 SC 959 Recreation (was on 959)
    13874: ("911", "993", "Turbo"),        # 993 Turbo GT2 Clubsport Tribute (was on 911 Race)
}

# Not the car it names. A factory "Tribute to Carrera RS Package" is excluded.
NOT_GENUINE = re.compile(
    r'Tribute(?! to Carrera RS)|Replica|Re-?creation|Reproduction|Evocation|'
    r'Conversion|Clone|Inspired|[\w.]+-Style\b|Specification',
    re.IGNORECASE,
)
NOT_A_CAR = re.compile(r"Tool Kit|Toolkit|Owner[’']?s Manual|Manual Collection", re.IGNORECASE)

# The rare name, stripped before reading the donor. "Turbo" is kept so a
# "993 Turbo GT2 Tribute" resolves to a Turbo.
_STRIP = re.compile(
    r'Slant\s*-?Nose|Slantnose|Conversion|Tribute|Replica|Re-?creation|Evocation|'
    r'Reproduction|Clone|Inspired|-Style|Specification|RSR(?:\s*3\.[0-9])?|RS\s*3\.[0-9]|'
    r'RS America|Carrera RS|GT2(?: RS)?|GT3 RS(?: 4\.0)?|S/T|Dakar|Sport Classic|'
    r'Lightweight|Touring|Sport|Clubsport|Speedster|\bRS\b|'
    # Engine-swap words: a 911SC with a turbo engine is still an SC.
    r'Turbo-?charged|\b930-Powered|3\.3L?\s+Turbo|Twin-Plug',
    re.IGNORECASE,
)
# Fallback when the donor title names no variant at all.
_DEFAULT = {
    "F-Body": "911", "G-Body": "911", "964": "Carrera 2", "993": "Carrera",
}


def not_genuine(rec) -> bool:
    title = rec.lot_title or ""
    if NOT_GENUINE.search(title):
        return True
    # The factory Flachbau (Sonderwunsch M505 / M506 / M491) was only built for
    # model years 1986-89 (earlier Sonderwunsch / "Special Wishes" cars and any
    # title naming a factory option code are exempt); an earlier "Slant Nose"
    # without one is somebody's conversion, and a title that says "Modified" is too.
    if (rec.generation, rec.variant) == ("G-Body", "Turbo 3.3 Slant Nose"):
        if re.search(r'Special Wishes|Sonderwunsch|\bM50[56]\b|\bM491\b', title, re.IGNORECASE):
            return False
        return (rec.year is not None and rec.year < 1986) or bool(
            re.search(r'\bModified\b', title, re.IGNORECASE))
    return False


def donor(rec) -> tuple[str, str]:
    cleaned = _STRIP.sub(" ", rec.lot_title or "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    gen = parse_generation(rec.model_line, rec.year, cleaned)
    var = parse_variant(rec.model_line, rec.year, cleaned)
    if var == "base":
        var = _DEFAULT.get(gen, "Carrera")
    return gen, var


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AuctionResult))
        plan: Counter = Counter()
        sample = []
        for rec in result.scalars().all():
            title = rec.lot_title or ""
            if rec.id in EXPLICIT:
                target = EXPLICIT[rec.id]
            elif rec.model_line != "911" or (rec.generation, rec.variant) not in RARE:
                continue
            elif NOT_A_CAR.search(title):
                target = ("Other", "Other", "base")
            elif not_genuine(rec) and rec.year is not None:
                gen, var = donor(rec)
                target = ("911", gen, var)
            else:
                continue
            if target == (rec.model_line, rec.generation, rec.variant):
                continue
            plan[(f"{rec.generation}/{rec.variant}", "/".join(target))] += 1
            if len(sample) < 60:
                sample.append(f"    #{rec.id} {rec.year} ${rec.sold_price} {title[:60]}  ->  {'/'.join(target)}")
            rec.model_line, rec.generation, rec.variant = target

        total = sum(plan.values())
        for (a, b), n in sorted(plan.items(), key=lambda kv: -kv[1]):
            print(f"  {n:3d}  {a}  ->  {b}")
        print()
        print("\n".join(sample[:60]))

        if apply:
            await session.commit()
            print(f"\nUpdated {total} record(s).")
        else:
            print(f"\nDRY RUN — {total} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
