#!/usr/bin/env python3
"""
Fix sold_date and thumbnail_url for all Mecum records.

Problems this fixes:
  - sold_date was stored from GraphQL `date` field (WordPress CMS timestamp),
    not the actual auction date. Real date is in `runDates.nodes[0].name`.
  - thumbnail_url was matched by slug, causing wrong images on duplicate-slug lots.

Now matches by `link` URL (contains numeric Mecum lot ID) which is unique per lot.

Usage (from backend/ directory):
    python data/migrate_mecum_dates_thumbs.py
"""
import asyncio
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
import certifi
from app.config import DATABASE_PATH
from app.database import AsyncSessionLocal, engine
from app.models.listing import AuctionResult
from sqlalchemy import select, update

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
GRAPHQL_URL = "https://mecum.stellate.sh"
PAGE_SIZE   = 100


def gql(query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req  = urllib.request.Request(GRAPHQL_URL, data=body, method="POST", headers={
        "User-Agent":   "Mozilla/5.0",
        "Content-Type": "application/json",
        "Accept":       "application/json",
        "Origin":       "https://www.mecum.com",
        "Referer":      "https://www.mecum.com/",
    })
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
        return json.loads(r.read().decode())


QUERY = """
query PorscheFix($size: Int!, $offset: Int!) {
  lots(first: $size, where: {
    taxQuery: {
      relation: AND
      taxArray: [
        { taxonomy: MAKE,       field: SLUG, terms: "porsche", operator: IN }
        { taxonomy: SALERESULT, field: SLUG, terms: "sold",    operator: IN }
      ]
    }
    offsetPagination: { size: $size, offset: $offset }
  }) {
    pageInfo { offsetPagination { total } }
    edges {
      node {
        link
        runDates { nodes { name } }
        images { url category }
      }
    }
  }
}
"""


async def migrate() -> None:
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.id, AuctionResult.auction_url).where(
                AuctionResult.auction_source == "Mecum",
                AuctionResult.auction_url.isnot(None),
            )
        )
        url_to_id: dict[str, int] = {row.auction_url: row.id for row in rows.fetchall()}

    print(f"Mecum records to update: {len(url_to_id)}")

    # Paginate GraphQL — build link → (run_date, thumbnail) map
    link_map: dict[str, dict] = {}
    offset = 0
    total  = None

    while True:
        try:
            resp = gql(QUERY, {"size": PAGE_SIZE, "offset": offset})
        except Exception as exc:
            print(f"  offset={offset} ERROR: {exc}")
            break

        data  = resp["data"]["lots"]
        edges = data.get("edges") or []
        if total is None:
            total = (data.get("pageInfo") or {}).get("offsetPagination", {}).get("total", 0)

        for edge in edges:
            node = edge["node"]
            link = node.get("link") or ""
            if not link:
                continue

            # Real auction date from runDates
            run_nodes = (node.get("runDates") or {}).get("nodes", [])
            run_date = None
            if run_nodes:
                try:
                    run_date = datetime.strptime(run_nodes[0]["name"], "%Y-%m-%d").date()
                except (ValueError, KeyError):
                    pass

            # First exterior image
            images = node.get("images") or []
            thumb = next(
                (img["url"] for img in images if img.get("category") == "Exterior"),
                None,
            )

            link_map[link] = {"run_date": run_date, "thumb": thumb}

        page = offset // PAGE_SIZE + 1
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE if total else "?"
        print(f"  page {page}/{total_pages} — {len(edges)} lots, {len(link_map)} mapped")

        if len(edges) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.3)

    # Build updates
    date_updates = thumb_updates = 0
    async with AsyncSessionLocal() as session:
        for url, record_id in url_to_id.items():
            entry = link_map.get(url)
            if not entry:
                continue
            vals = {}
            if entry["run_date"]:
                vals["sold_date"] = entry["run_date"]
                date_updates += 1
            if entry["thumb"]:
                vals["thumbnail_url"] = entry["thumb"]
                thumb_updates += 1
            if vals:
                await session.execute(
                    update(AuctionResult)
                    .where(AuctionResult.id == record_id)
                    .values(**vals)
                )
        await session.commit()

    matched = sum(1 for url in url_to_id if url in link_map)
    print(f"\nMatched {matched} of {len(url_to_id)} records")
    print(f"  sold_date updated:   {date_updates}")
    print(f"  thumbnail updated:   {thumb_updates}")
    print(f"Database: {DATABASE_PATH}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
