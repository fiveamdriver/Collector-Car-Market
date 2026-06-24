#!/usr/bin/env python3
"""
Reclassify Gooding & Company race car records to proper model_line / generation / variant.

Usage (from backend/ directory):
    python data/migrate_race_cars.py

Safe to re-run — already-correct records are left untouched.
"""
import asyncio
import re
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal, engine, Base
from app.models.listing import AuctionResult
from sqlalchemy import select


def get_911_generation(year: int) -> str:
    if year <= 1973: return "F-Body"
    if year <= 1989: return "G-Body"
    if year <= 1994: return "964"
    if year <= 1998: return "993"
    if year <= 2012: return "997"
    if year <= 2019: return "991"
    return "992"


def classify(title: str, year: int) -> tuple[str, str, str] | None:
    """Return (model_line, generation, variant) or None if not a race car."""
    t = title

    # ── 911-based race cars ───────────────────────────────────────────────────
    is_911_rsr   = bool(re.search(r'\bRSR\b', t))
    is_gt1       = bool(re.search(r'\bGT1\b', t))
    is_gt3_rsr   = bool(re.search(r'GT3.*RSR|GT3 RSR', t))
    is_cup       = bool(re.search(r'\bCup\b', t)) and is_911_rsr
    is_rsr_turbo = bool(re.search(r'RSR.*Turbo|Turbo.*RSR', t))

    if is_gt1 or is_gt3_rsr or is_cup or is_rsr_turbo or is_911_rsr:
        # Only classify as 911 Race if title actually contains "911" or is clearly 911-based
        # (avoids false-positives for RSR on non-911 cars, though Gooding rarely has those)
        if re.search(r'\b911\b|Carrera RSR|Carrera.*RSR|GT3 RSR|993 Cup|964.*RSR|997.*RSR|991.*RSR|992.*RSR', t):
            if is_gt1:
                return ("911 GT1", "911 GT1", "base")
            gen = get_911_generation(year)
            if is_gt3_rsr:     variant = "GT3 RSR"
            elif is_cup:       variant = "Cup 3.8 RSR"
            elif is_rsr_turbo: variant = "RSR Turbo"
            else:              variant = "RSR"
            return ("911 Race", gen, variant)

    # ── Standalone race models — word-boundary safe ───────────────────────────
    if re.search(r'\b917\b', t):
        return ("917", "917", "base")

    if re.search(r'\b962\b', t):
        return ("962", "962", "base")

    if re.search(r'\b956\b', t):
        return ("956", "956", "base")

    if re.search(r'\b935\b', t):
        return ("935", "935", "base")

    if re.search(r'\b934\b', t):
        return ("934", "934", "base")

    if re.search(r'\b908\b', t):
        return ("908", "908", "base")

    if re.search(r'\b907\b', t):
        return ("907", "907", "base")

    if re.search(r'\b906\b', t):
        return ("906", "906", "base")

    if re.search(r'\b904\b', t):
        return ("904", "904", "base")

    # RS60 / RS61 before generic 550 (RS60 is a 718-chassis car, not a 550)
    if re.search(r'\bRS6[01]\b', t):
        return ("RS60", "RS60", "base")

    # 718 RSK — the historic 1950s race car (not modern 718 Cayman/Boxster)
    if re.search(r'\b718\b', t) and re.search(r'\bRSK?\b', t):
        return ("718 RSK", "718 RSK", "base")

    # 550 Spyder (incl. 550/1500 RS)
    if re.search(r'\b550\b', t):
        return ("550", "550", "base")

    # RS Spyder LMP (2007 Porsche RS Spyder Evo) — only if not a 550-family car
    if re.search(r'\bRS Spyder\b', t) and not re.search(r'\b550\b', t):
        return ("RS Spyder", "RS Spyder", "base")

    return None


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult).where(AuctionResult.auction_source == "Gooding & Company")
        )
        records = rows.scalars().all()

    updates = []
    for r in records:
        result = classify(r.lot_title or "", r.year)
        if result is None:
            continue
        ml, gen, var = result
        if r.model_line == ml and r.generation == gen and r.variant == var:
            continue  # already correct
        updates.append((r.id, ml, gen, var, r.model_line, r.generation, r.variant, r.lot_title))

    print(f"Records to update: {len(updates)}")
    for id_, ml, gen, var, old_ml, old_gen, old_var, title in updates[:10]:
        print(f"  [{id_}] {old_ml}/{old_gen}/{old_var} → {ml}/{gen}/{var}  | {title[:60]}")
    if len(updates) > 10:
        print(f"  ... and {len(updates) - 10} more")

    async with AsyncSessionLocal() as session:
        for id_, ml, gen, var, *_ in updates:
            r = await session.get(AuctionResult, id_)
            r.model_line = ml
            r.generation = gen
            r.variant    = var
        await session.commit()

    print(f"\nDone — updated {len(updates)} records.")


if __name__ == "__main__":
    asyncio.run(migrate())
