#!/usr/bin/env python3
"""
Split the 935 race line into Classic (original Group 5 cars) and Modern
(2018 GT2 RS-based 935) generations, mirroring how 911 Race opens into
generations. Covers every auction source, not just Gooding.

Usage (from backend/ directory):
    python data/migrate_935_generations.py

Safe to re-run — already-correct records are left untouched.
"""
import asyncio
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from data.migrate_race_cars import get_935_generation
from sqlalchemy import select


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(AuctionResult.model_line == "935")
        )
        changed = 0
        for rec in result.scalars().all():
            gen = get_935_generation(rec.year)
            if rec.generation == gen:
                continue
            print(f"  #{rec.id}: {rec.generation} -> {gen} | {rec.year} {(rec.lot_title or '')[:60]}")
            rec.generation = gen
            changed += 1

        await session.commit()
        print(f"Updated {changed} record(s).")


if __name__ == "__main__":
    asyncio.run(main())
