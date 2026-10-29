#!/usr/bin/env python3
"""
Re-derive sold_date for Broad Arrow rows from their lot URL's event code.

Broad Arrow lot URLs name the sale only by a short code (`/vehicles/ql26_r0165/`)
and nothing in the lot payload carries a date, so the date comes from the
AUCTION_EVENTS lookup in broad_arrow_ingest.py.  That table listed three codes
while twenty-nine were in use, and every unlisted code fell back to January 1 of
the code's year.  The result: 396 of 478 stored rows (83%) carried a fabricated
January 1 date, indistinguishable downstream from a real sale date and plotted at
the wrong end of every price history.

A second bug hid three more sales.  The event-code pattern did not allow the
trailing letter that the Global Icons sales use for their region (gi26e / gi26u /
gi26v / gi26z), so those lots matched no code at all and were stored with no date.

AUCTION_EVENTS is now exhaustive and the January 1 fallback is gone.  This
backfills the rows written before that, resolving each row's date the same way a
fresh ingest now would.  Re-running the ingest cannot do this itself — it dedupes
on auction_url and skips every row already stored.

Usage (from backend/ directory):
    python data/migrate_broad_arrow_dates.py            # dry run
    python data/migrate_broad_arrow_dates.py --apply    # writes the changes

Safe to re-run — rows that already hold the right date are left untouched.
"""
import asyncio
import os
import sys
from collections import Counter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, "data"))

import app.models  # noqa: F401
from app.database import AsyncSessionLocal, engine
from app.models.listing import AuctionResult
from broad_arrow_ingest import AUCTION_EVENTS, event_date, extract_event_code
from sqlalchemy import select


async def main() -> None:
    apply = "--apply" in sys.argv

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(AuctionResult).where(AuctionResult.auction_source == "Broad Arrow")
        )).scalars().all()

        print(f"Broad Arrow rows: {len(rows)}")

        changes: list[tuple[AuctionResult, object, object]] = []
        unresolved: Counter[str] = Counter()
        no_url = 0

        for row in rows:
            if not row.auction_url:
                no_url += 1
                continue
            code = extract_event_code(row.auction_url)
            if code is None:
                unresolved["<no code in URL>"] += 1
                continue
            resolved = event_date(code)
            if resolved is None:
                unresolved[code] += 1
                continue
            if row.sold_date != resolved:
                changes.append((row, row.sold_date, resolved))

        # Report by event so a wrong table entry is obvious before it is written.
        by_event: dict[str, Counter] = {}
        for row, old, new in changes:
            code = extract_event_code(row.auction_url) or "?"
            by_event.setdefault(code, Counter())[f"{old} -> {new}"] += 1

        print(f"\n{len(changes)} row(s) would change date:\n")
        for code in sorted(by_event, key=lambda c: AUCTION_EVENTS[c]):
            for transition, n in by_event[code].most_common():
                print(f"  {code:<7} {n:>4} rows   {transition}")

        if unresolved:
            print(f"\n{sum(unresolved.values())} row(s) left with no date "
                  f"(event code not in AUCTION_EVENTS):")
            for code, n in unresolved.most_common():
                print(f"  {code:<7} {n:>4} rows")
            print("  Run `python data/broad_arrow_events.py` to extend the table.")
        if no_url:
            print(f"\n{no_url} row(s) have no auction_url and cannot be resolved.")

        if not apply:
            print("\nDry run — pass --apply to write these changes.")
            await engine.dispose()
            return

        for row, _old, new in changes:
            row.sold_date = new
        await session.commit()
        print(f"\nApplied — {len(changes)} row(s) updated.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
