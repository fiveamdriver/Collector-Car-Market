#!/usr/bin/env python3
"""
Targeted BaT ingest for the transaxle models (924/944/968/928) and the 914.

The main bat_ingest.py re-crawls all ~64 model configs and commits only once at
the very end, so a long run that gets interrupted saves nothing.  This runner
processes just the newly-added transaxle/914 CONFIGS entries and commits after
each config, so progress is durable.  Dedup is by auction_url against all
existing rows, so re-running is safe.

Usage (from backend/ directory):
    python -u data/bat_ingest_transaxle.py
"""
import os
import sys
import time

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import asyncio

import app.models  # noqa: F401
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from data.bat_ingest import CONFIGS, fetch_page, map_record
from sqlalchemy import select

TARGET_MODEL_LINES = {"914", "924", "944", "968", "928"}


async def ingest() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.auction_url).where(AuctionResult.auction_url.isnot(None))
        )
        existing: set[str] = {r[0] for r in rows.fetchall()}
    print(f"Existing URLs loaded: {len(existing)}")

    configs = [c for c in CONFIGS if c["model_line"] in TARGET_MODEL_LINES]
    print(f"Target configs: {[c['name'] for c in configs]}\n")

    grand_total = 0
    for cfg in configs:
        ids, model_line, variant = cfg["ids"], cfg["model_line"], cfg["variant"]
        queued: list[dict] = []
        fetched = skipped = 0
        page = 1
        while True:
            try:
                items = fetch_page(ids, page)
            except Exception as exc:
                print(f"  [{cfg['name']}] page {page} ERROR: {exc}")
                break
            if not items:
                break
            fetched += len(items)
            for raw in items:
                rec = map_record(raw, model_line, variant)
                if rec is None:
                    continue
                url = rec.get("auction_url")
                if url and url in existing:
                    skipped += 1
                    continue
                if url:
                    existing.add(url)
                queued.append(rec)
            page += 1
            time.sleep(2)

        if queued:
            async with AsyncSessionLocal() as session:
                session.add_all([AuctionResult(**r) for r in queued])
                await session.commit()
        grand_total += len(queued)
        print(f"  [{cfg['name']:10}] fetched {fetched} | inserted {len(queued)} | skipped {skipped}")
        time.sleep(3)

    print(f"\nDone — inserted {grand_total} new transaxle/914 rows.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
