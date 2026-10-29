#!/usr/bin/env python3
"""
Classify F-Body (1963-1973) 911s into their proper trim variants.

Fixes three problems:
  1. ~560 F-Body records sat in hidden 'base'/'Targa' buckets because titles
     like "1973 Porsche 911 2.4 S" or "1968 Porsche 911 L" were never parsed
     into 911S/911T/911E/911L/911R.
  2. An old classifier bug turned 1968 -> generation "968" and 1959 ->
     generation "959" (26 + 6 records), hiding two genuine 911Rs.
  3. The gen-"959" records are Porsche-Diesel tractors — moved to hidden
     model_line 'Other' so they stop counting as 911s.

'Carrera RS 2.7 Lightweight' and mis-labelled 'Carrera 2.7' RS cars fold into
'Carrera RS 2.7' (lightweights stay on the RS 2.7 card by design).

Usage (from backend/ directory):
    python data/migrate_fbody_variants.py

Safe to re-run — already-correct records are left untouched.
"""
import asyncio
import re
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from sqlalchemy import select

NOT_A_CAR   = re.compile(r'Porsche[- ]Diesel|Tractor|Jagdwagen|\b597\b', re.IGNORECASE)
RS_27       = re.compile(r'Carrera RS 2\.7|Carrera 2\.7 RS|RS 2\.7|Carrera RS\b')
S_T         = re.compile(r'\bS/T\b|911 ST\b')
R_SLASH_T   = re.compile(r'\bR/T\b')          # aftermarket R/Touring builds
T_SLASH_R   = re.compile(r'\bT/R\b')          # factory 911 T/R rally spec
R_911       = re.compile(r'911[ -]?R\b')
L_911       = re.compile(r'911[ -]?L\b|2\.0 L\b')
T_911       = re.compile(r'911[ -]?T\b|2\.[024][ -]?T\b')
E_911       = re.compile(r'911[ -]?E\b|2\.[024][ -]?E\b')
S_911       = re.compile(r'911[ -]?S\b|2\.[024][ -]?S\b|\bS (Coupe|Coupé|Targa)')
TARGA       = re.compile(r'Targa', re.IGNORECASE)


def classify(title: str) -> str:
    if RS_27.search(title):     return "Carrera RS 2.7"
    if S_T.search(title):       return "S/T"
    if R_SLASH_T.search(title): return "911"
    if T_SLASH_R.search(title): return "911T"
    if R_911.search(title):     return "911R"
    if L_911.search(title):     return "911L"
    if T_911.search(title):     return "911T"
    if E_911.search(title):     return "911E"
    if S_911.search(title):     return "911S"
    if TARGA.search(title):     return "Targa"
    return "911"


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(
                AuctionResult.model_line == "911",
                AuctionResult.generation.in_(["F-Body", "968", "959"]),
            )
        )
        records = result.scalars().all()

        moved = {}
        for rec in records:
            t = rec.lot_title or ""

            if NOT_A_CAR.search(t):
                target = ("Other", "Other", "base")
            else:
                target = ("911", "F-Body", classify(t))

            if (rec.model_line, rec.generation, rec.variant) == target:
                continue
            key = f"{target[0]} / {target[1]} / {target[2]}"
            moved[key] = moved.get(key, 0) + 1
            if target[2] in ("911R", "S/T") or target[0] == "Other":
                print(f"  #{rec.id}: {rec.generation}/{rec.variant} -> {key} | {t[:60]}")
            rec.model_line, rec.generation, rec.variant = target

        await session.commit()
        for key in sorted(moved):
            print(f"  {moved[key]:4d} -> {key}")
        print(f"Moved {sum(moved.values())} record(s) total.")


if __name__ == "__main__":
    asyncio.run(main())
