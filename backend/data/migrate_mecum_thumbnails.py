#!/usr/bin/env python3
"""
Backfill thumbnail_url for existing Mecum records.

Paginates through the same GraphQL query used by mecum_ingest.py,
builds a slug → first-exterior-image-url map, then updates DB records
where thumbnail_url IS NULL.

Usage (from backend/ directory):
    python data/migrate_mecum_thumbnails.py
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
LOT_BASE    = "https://www.mecum.com/lots"
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


IMAGES_QUERY = """
query PorscheThumbnails($size: Int!, $offset: Int!) {
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
        slug
        images { url category }
      }
    }
  }
}
"""


async def migrate() -> None:
    # Load existing Mecum records missing a thumbnail
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.id, AuctionResult.auction_url).where(
                AuctionResult.auction_source == "Mecum",
                AuctionResult.thumbnail_url.is_(None),
            )
        )
        missing: dict[str, int] = {}  # lot_url → id
        for row in rows.fetchall():
            if row.auction_url:
                missing[row.auction_url] = row.id

    print(f"Mecum records missing thumbnail: {len(missing)}")
    if not missing:
        print("Nothing to do.")
        return

    # Paginate GraphQL to build slug → thumbnail map
    slug_to_thumb: dict[str, str] = {}
    offset = 0
    total  = None

    while True:
        try:
            resp = gql(IMAGES_QUERY, {"size": PAGE_SIZE, "offset": offset})
        except Exception as exc:
            print(f"  offset={offset} ERROR: {exc}")
            break

        data  = resp["data"]["lots"]
        edges = data.get("edges") or []
        if total is None:
            total = (data.get("pageInfo") or {}).get("offsetPagination", {}).get("total", 0)

        for edge in edges:
            node = edge["node"]
            slug = node.get("slug") or ""
            if not slug:
                continue
            images = node.get("images") or []
            thumb = next(
                (img["url"] for img in images if img.get("category") == "Exterior"),
                None,
            )
            if thumb:
                slug_to_thumb[slug] = thumb

        page = offset // PAGE_SIZE + 1
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE if total else "?"
        print(f"  page {page}/{total_pages} — {len(edges)} lots, {len(slug_to_thumb)} thumbs so far")

        if len(edges) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.5)

    # Match slug_to_thumb against missing records
    updates: list[tuple[int, str]] = []
    for lot_url, record_id in missing.items():
        # lot_url looks like https://www.mecum.com/lots/<slug>/
        slug = lot_url.rstrip("/").rsplit("/", 1)[-1]
        thumb = slug_to_thumb.get(slug)
        if thumb:
            updates.append((record_id, thumb))

    print(f"\nMatched {len(updates)} thumbnails out of {len(missing)} missing")

    if not updates:
        print("No updates to apply.")
        return

    async with AsyncSessionLocal() as session:
        for record_id, thumb_url in updates:
            await session.execute(
                update(AuctionResult)
                .where(AuctionResult.id == record_id)
                .values(thumbnail_url=thumb_url)
            )
        await session.commit()

    print(f"Updated {len(updates)} Mecum records with thumbnail URLs")
    print(f"Database: {DATABASE_PATH}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
