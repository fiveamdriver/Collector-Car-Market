#!/usr/bin/env python3
"""
Reclassify Race Cars For You records using the updated classify() logic.

Safe to re-run — already-correct records are skipped.

Usage (from backend/ directory):
    python data/migrate_rcfy_classify.py
"""
import asyncio
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from sqlalchemy import select

# Import classifier from the ingest script
sys.path.insert(0, os.path.join(BACKEND_DIR, "data"))
from rcfy_ingest import classify


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult).where(AuctionResult.auction_source == "Race Cars For You")
        )
        records = rows.scalars().all()

    updates = []
    for r in records:
        ml, gen, var = classify(r.lot_title or "", r.year)
        if r.model_line == ml and r.generation == gen and r.variant == var:
            continue
        updates.append((r.id, ml, gen, var, r.model_line, r.generation, r.variant, r.lot_title))

    print(f"Records to update: {len(updates)}")
    for id_, ml, gen, var, old_ml, old_gen, old_var, title in updates[:20]:
        print(f"  [{id_}] {old_ml}/{old_gen}/{old_var} → {ml}/{gen}/{var}  | {(title or '')[:60]}")
    if len(updates) > 20:
        print(f"  ... and {len(updates) - 20} more")

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
