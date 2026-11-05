#!/usr/bin/env python3
"""Fill missing Mecum thumbnails (2026-11-04). The ingest used to take only photos
tagged 'Exterior', so lots with an untagged gallery got none. Pages the same
GraphQL query and fills thumbnail_url only where it is NULL.

    python data/backfill_mecum_thumbnails.py          # dry run
    python data/backfill_mecum_thumbnails.py --apply
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from data.mecum_ingest import LOTS_QUERY, PAGE_SIZE, gql, pick_thumbnail  # noqa: E402


async def main(apply: bool):
    async with AsyncSessionLocal() as s:
        missing = {r[0].rstrip("/"): r[1] for r in (await s.execute(text(
            "SELECT auction_url, id FROM auction_results WHERE auction_url LIKE '%mecum.com%' "
            "AND (thumbnail_url IS NULL OR thumbnail_url = '')"))).fetchall()}
    print(f"{len(missing)} Mecum rows without a thumbnail")
    found, no_photo, offset, total = {}, 0, 0, None
    while total is None or offset < total:
        d = gql(LOTS_QUERY, {"size": PAGE_SIZE, "offset": offset})["data"]["lots"]
        total = d["pageInfo"]["offsetPagination"]["total"]
        for e in d["edges"]:
            n = e["node"]
            rid = missing.get((n.get("link") or "").rstrip("/"))
            if rid is None:
                continue
            url = pick_thumbnail(n.get("images") or [])
            if url:
                found[rid] = url
            else:
                no_photo += 1
        offset += PAGE_SIZE
        time.sleep(0.5)
    print(f"thumbnail found for {len(found)}; Mecum has no usable photo for {no_photo}; "
          f"{len(missing) - len(found) - no_photo} not matched in the feed")
    if apply and found:
        async with AsyncSessionLocal() as s:
            await s.execute(text("UPDATE auction_results SET thumbnail_url = :u WHERE id = :i "
                                 "AND (thumbnail_url IS NULL OR thumbnail_url = '')"),
                            [{"u": u, "i": i} for i, u in found.items()])
            await s.commit()
        print("applied")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
