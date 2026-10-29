#!/usr/bin/env python3
"""
Export the database to a dated, gzipped CSV per table — a private safety copy.

The database is hosted PostgreSQL, so its data is not in git (and must not be:
this repo is public, and the rows are scraped auction records). Run this before
any bulk migration or ingest, and keep the output outside the repo.

Usage (from backend/ directory):
    python data/backup_db.py                 # -> ~/Projects/CollectorCarMarket-data/backups/<date>/
    python data/backup_db.py /some/dir       # -> /some/dir/<date>/

Uses the app's own connection (app.database), so credentials stay in backend/.env.
"""
import asyncio
import csv
import gzip
import os
import sys
from datetime import date

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import ActiveListing, AuctionResult
from sqlalchemy import select

DEFAULT_ROOT = os.path.expanduser("~/Projects/CollectorCarMarket-data/backups")


async def dump(model, out_dir: str) -> int:
    cols = [c.name for c in model.__table__.columns]
    path = os.path.join(out_dir, f"{model.__tablename__}.csv.gz")
    n = 0
    async with AsyncSessionLocal() as session:
        result = await session.stream_scalars(select(model))
        with gzip.open(path, "wt", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            async for row in result:
                w.writerow([getattr(row, c) for c in cols])
                n += 1
    print(f"  {model.__tablename__}: {n} rows -> {path} ({os.path.getsize(path) // 1024} KB)")
    return n


async def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT
    out_dir = os.path.join(root, date.today().isoformat())
    os.makedirs(out_dir, exist_ok=True)
    for model in (AuctionResult, ActiveListing):
        await dump(model, out_dir)
    print(f"\nBackup written to {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
