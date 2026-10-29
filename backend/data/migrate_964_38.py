#!/usr/bin/env python3
"""
Reclassify factory 964 Carrera RS 3.8 (street car) records into a dedicated
'RS 3.8' variant under 911 / 964.

Matches lot titles containing "RS 3.8" (including "3.8-Litre" forms) while
excluding engine swaps, replicas, and backdates. The competition RSR 3.8s
are handled by migrate_race_cleanup.py (911 Race / 964 / RSR 3.8).

Usage (from backend/ directory):
    python data/migrate_964_38.py

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
from app.utils.variants import is_964_rs_38
from sqlalchemy import select


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AuctionResult).where(
                AuctionResult.generation == "964",
                AuctionResult.model_line.in_(["911", "911 Race"]),
            )
        )
        records = result.scalars().all()

        changed = 0
        for rec in records:
            if not rec.lot_title or not is_964_rs_38(rec.lot_title):
                continue
            if rec.model_line == "911" and rec.variant == "RS 3.8":
                continue
            print(f"  #{rec.id}: {rec.model_line} / {rec.variant} -> 911 / RS 3.8 | {rec.lot_title[:70]}")
            rec.model_line = "911"
            rec.variant = "RS 3.8"
            changed += 1

        await session.commit()
        print(f"Updated {changed} record(s).")


if __name__ == "__main__":
    asyncio.run(main())
