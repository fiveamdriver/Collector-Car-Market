#!/usr/bin/env python3
"""
Fix auction_url for existing Mecum records.

Old format: https://www.mecum.com/lots/<slug>/
New format: https://www.mecum.com/lots/<id>/<slug>/  (from GraphQL `link` field)

Usage (from backend/ directory):
    python data/migrate_mecum_urls.py
"""
import asyncio
import json
import os
import ssl
import sys
import time
import urllib.request

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


LINKS_QUERY = """
query PorscheLinks($size: Int!, $offset: Int!) {
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
    edges { node { slug link date hammerPrice } }
  }
}
"""


async def migrate() -> None:
    # Load all Mecum records — match by (slug, sold_date, sold_price) to handle duplicate slugs
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.id, AuctionResult.auction_url,
                   AuctionResult.sold_date, AuctionResult.sold_price).where(
                AuctionResult.auction_source == "Mecum",
            )
        )
        # (slug, date_str, price) → id
        key_to_id: dict[tuple, int] = {}
        for row in rows.fetchall():
            if row.auction_url:
                slug = row.auction_url.rstrip("/").rsplit("/", 1)[-1]
                date_str = str(row.sold_date)[:10] if row.sold_date else ""
                key_to_id[(slug, date_str, row.sold_price)] = row.id

    print(f"Mecum records to fix: {len(key_to_id)}")

    # Paginate GraphQL to build (slug, date, price) → correct link map
    slug_to_link: dict[tuple, str] = {}
    offset = 0
    total  = None

    while True:
        try:
            resp = gql(LINKS_QUERY, {"size": PAGE_SIZE, "offset": offset})
        except Exception as exc:
            print(f"  offset={offset} ERROR: {exc}")
            break

        data  = resp["data"]["lots"]
        edges = data.get("edges") or []
        if total is None:
            total = (data.get("pageInfo") or {}).get("offsetPagination", {}).get("total", 0)

        for edge in edges:
            node  = edge["node"]
            slug  = node.get("slug") or ""
            link  = node.get("link") or ""
            date  = (node.get("date") or "")[:10]
            price_raw = node.get("hammerPrice") or ""
            try:
                price = int(str(price_raw).replace(",", "").replace("$", ""))
            except (ValueError, TypeError):
                price = 0
            if slug and link:
                slug_to_link[(slug, date, price)] = link

        page = offset // PAGE_SIZE + 1
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE if total else "?"
        print(f"  page {page}/{total_pages} — {len(edges)} lots, {len(slug_to_link)} links mapped")

        if len(edges) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.3)

    # Match by (slug, date, price) — prevents wrong URL on duplicate slugs
    updates: list[tuple[int, str]] = []
    for key, record_id in key_to_id.items():
        new_link = slug_to_link.get(key)
        if new_link:
            updates.append((record_id, new_link))

    print(f"\nMatched {len(updates)} of {len(key_to_id)} records")

    if not updates:
        print("No updates to apply.")
        return

    async with AsyncSessionLocal() as session:
        for record_id, new_url in updates:
            await session.execute(
                update(AuctionResult)
                .where(AuctionResult.id == record_id)
                .values(auction_url=new_url)
            )
        await session.commit()

    print(f"Updated {len(updates)} Mecum auction URLs")
    print(f"Database: {DATABASE_PATH}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
