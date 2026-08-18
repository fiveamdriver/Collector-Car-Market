#!/usr/bin/env python3
"""
Decode HTML entities left in lot titles.

Broad Arrow's JSON-LD carries HTML-escaped text, and the title was stored without
unescaping it, so lots reached the site reading
`911 Turbo S &quot;Package&quot;`. broad_arrow_ingest.py now unescapes at the
source; this cleans up the rows written before that fix.

Only the display text changes — model line, generation and variant are left alone,
since the entities sit around quoted nicknames and never affected parsing.

Usage (from backend/ directory):
    python data/migrate_html_entities.py            # dry run
    python data/migrate_html_entities.py --apply    # writes the changes

Safe to re-run — already-clean titles are left untouched.
"""
import asyncio
import html
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import AsyncSessionLocal
from app.models.listing import AuctionResult
from sqlalchemy import select


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AuctionResult))
        records = result.scalars().all()

        changed = 0
        sources: dict[str, int] = {}
        for rec in records:
            title = rec.lot_title
            if not title:
                continue
            decoded = html.unescape(title)
            if decoded == title:
                continue
            print(f"  #{rec.id}: {title[:52]}")
            print(f"       -> {decoded[:52]}")
            rec.lot_title = decoded
            changed += 1
            sources[rec.auction_source] = sources.get(rec.auction_source, 0) + 1

        print()
        for src in sorted(sources, key=lambda s: -sources[s]):
            print(f"  {src}: {sources[src]} record(s)")

        if apply:
            await session.commit()
            print(f"\nUpdated {changed} record(s).")
        else:
            print(f"\nDRY RUN — {changed} record(s) would change. Re-run with --apply to write.")


if __name__ == "__main__":
    asyncio.run(main())
