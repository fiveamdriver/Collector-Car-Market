#!/usr/bin/env python3
"""
Ingest Porsche auction data from Gooding & Company's GraphQL API.

Usage (from backend/ directory):
    python data/gooding_ingest.py

No API key or authentication required. Re-running is safe — duplicates are
skipped by auction_url.
"""
import asyncio
import certifi
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.config import DATABASE_PATH
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from sqlalchemy import select

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

GRAPHQL_URL  = "https://cdn.goodingco.com/graphql"
LOT_BASE_URL = "https://www.goodingco.com/lot/"
CDN_BASE     = "https://res.cloudinary.com/goodingco/image/upload/"
HITS_PER_PAGE = 15
QUERY_HASH   = "0749eee74b0c4cf20bde3cd2a79b36ca364b6d1e4364ce3295a1ae4dd090706a"


# ── Generation lookups (mirror bat_ingest.py) ────────────────────────────────

def get_911_generation(year: int) -> str:
    if year <= 1973: return "F-Body"
    if year <= 1989: return "G-Body"
    if year <= 1994: return "964"
    if year <= 1998: return "993"
    if year <= 2001: return "996.1"
    if year <= 2005: return "996.2"
    if year <= 2008: return "997.1"
    if year <= 2012: return "997.2"
    if year <= 2016: return "991.1"
    if year <= 2019: return "991.2"
    return "992"


def get_cayman_generation(year: int) -> str:
    if year <= 2008: return "987.1"
    if year <= 2012: return "987.2"
    if year <= 2016: return "981"
    return "718"


def get_boxster_generation(year: int) -> str:
    if year <= 2004: return "986"
    if year <= 2008: return "987.1"
    if year <= 2012: return "987.2"
    if year <= 2016: return "981"
    return "718"


# ── Model / variant parsing ───────────────────────────────────────────────────

# Ordered longest-match first to avoid partial collisions (e.g. "930" before "911")
PORSCHE_MODEL_LINES = [
    ("918 Spyder", "918 Spyder"),
    ("959",         "959"),
    ("Cayenne",     "Cayenne"),
    ("Panamera",    "Panamera"),
    ("Taycan",      "Taycan"),
    ("Boxster",     "Boxster"),
    ("Cayman",      "Cayman"),
    ("968",         "968"),
    ("944",         "944"),
    ("930",         "911"),    # 930 Turbo → model_line 911
    ("928",         "928"),
    ("924",         "924"),
    ("914",         "914"),
    ("912E",        "912"),
    ("912",         "912"),
    ("356",         "356"),
    ("904",         "904"),
    # Race cars — word-boundary matched to avoid year-digit false positives
    ("962",         "962"),
    ("956",         "956"),
    ("935",         "935"),
    ("934",         "934"),
    ("917",         "917"),
    ("908",         "908"),
    ("907",         "907"),
    ("906",         "906"),
    ("Carrera GT",  "Carrera GT"),  # after all numeric models; uses word-boundary match
    ("911",         "911"),
]

_356_VARIANTS = ["Speedster", "Roadster", "Cabriolet", "Coupe", "Notchback"]

_911_VARIANTS = [
    "GT3 RS 4.0", "GT3 RS", "GT3",
    "GT2 RS", "GT2",
    "Turbo S", "Turbo",
    "Sport Classic", "S/T", "Dakar",
    "Speedster", "Targa",
    "RS America", "Carrera RS 3.0", "Carrera RS 2.7", "Carrera RS",
    "Carrera 4S", "Carrera 4", "Carrera S", "Carrera GTS", "Carrera T",
    "Carrera 3.2", "Carrera 2.7",
    "Carrera", "Singer",
    "SC", "911S",
]

_944_VARIANTS = ["Turbo S", "Turbo", "S2", "S"]
_924_VARIANTS = ["Carrera GT", "Carrera GTS", "Turbo"]


def parse_model_line(text: str) -> str:
    for token, ml in PORSCHE_MODEL_LINES:
        if token == "Carrera GT":
            if re.search(r'\bCarrera GT\b', text):
                return ml
        elif token[0].isdigit():
            if re.search(r'\b' + re.escape(token) + r'\b', text):
                return ml
        elif token in text:
            return ml
    return "911"


def parse_generation(model_line: str, year: int, text: str) -> str:
    if model_line == "911":
        return get_911_generation(year)
    if model_line == "Cayman":
        return get_cayman_generation(year)
    if model_line == "Boxster":
        return get_boxster_generation(year)
    if model_line == "356":
        if year <= 1955: return "Pre-A"
        if year <= 1959: return "356 A"
        if year <= 1963: return "356 B"
        return "356 C"
    if model_line == "944":
        if "Turbo" in text: return "944 Turbo"
        if "S2" in text:    return "944 S2"
        return "944"
    return model_line  # 912, 914, 924, 928, 968, 959, Carrera GT, 918 Spyder, etc.


def parse_variant(model_line: str, year: int, text: str) -> str:
    if model_line == "911":
        gen = get_911_generation(year)
        if gen == "G-Body":
            if "Slant Nose" in text:           return "Turbo 3.3 Slant Nose"
            if "MFI" in text:                  return "Carrera 2.7 MFI"
            if "Carrera 2.7" in text:          return "Carrera 2.7"
            if "Carrera RS 3.0" in text:       return "Carrera RS 3.0"
            if "Carrera RS" in text:           return "Carrera RS 2.7"
            if "Speedster" in text:            return "Speedster"
            if "Turbo" in text or "930" in text: return "930 Turbo"
            if "Targa" in text:                return "Targa"
            if "Carrera" in text and year <= 1977: return "Carrera 2.7"
            if "SC" in text:                   return "SC"
            if "Carrera 3.2" in text or ("Carrera" in text and year >= 1984):
                                               return "Carrera 3.2"
            if "911S" in text or "911 S" in text: return "911S"
            return "base"
        if gen == "F-Body":
            if "Carrera RS 2.7" in text or "Carrera RS" in text: return "Carrera RS 2.7"
            if "Carrera 2.7" in text:          return "Carrera 2.7"
            if "911S" in text:                 return "911S"
            if "Targa" in text:                return "Targa"
            return "base"
        for pat in _911_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line == "356":
        for pat in _356_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line == "944":
        for pat in _944_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line == "924":
        for pat in _924_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line in ("Cayman", "Boxster"):
        for pat in ["GT4 RS", "GT4", "GTS", "Spyder RS", "Spyder"]:
            if pat in text:
                return pat
        if re.search(r'\bR\b', text): return "R"
        if re.search(r'\bS\b', text): return "S"
        return "base"

    return "base"


def parse_paint_to_sample(text: str) -> bool | None:
    if re.search(r'paint[-\s]to[-\s]sample|PTS', text, re.IGNORECASE):
        return True
    return None


# ── GraphQL fetch ─────────────────────────────────────────────────────────────

def fetch_page(page_number: int) -> tuple[list[dict], int]:
    """Return (vehicles, nb_pages) for the given 1-based page number."""
    variables = {
        "filtersInput": {"make": ["Porsche"], "auctionType": [], "itemType": [], "venue": [], "auctionYear": []},
        "sortBy": "ENDING_SOONEST",
        "pageNumber": page_number,
    }
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": QUERY_HASH}}
    params = urllib.parse.urlencode({
        "operationName": "GetVehiclesAndFilters",
        "variables":     json.dumps(variables, separators=(",", ":")),
        "extensions":    json.dumps(extensions, separators=(",", ":")),
    })
    url = f"{GRAPHQL_URL}?{params}"
    req = urllib.request.Request(url, headers={
        "Accept":        "*/*",
        "Authorization": "Bearer",
        "Content-Type":  "application/json",
        "Origin":        "https://www.goodingco.com",
        "User-Agent":    "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
        payload = json.loads(resp.read().decode())
    gv = payload["data"]["getVehicles"]
    return gv["vehicles"], gv["nbPages"]


# ── Record mapper ─────────────────────────────────────────────────────────────

def map_record(v: dict) -> dict | None:
    """Map a Gooding vehicle object to an auction_results row dict."""
    # Only completed, sold lots
    if v.get("activeAuction") != "false":
        return None
    sale_price_raw = v.get("salePrice") or ""
    if not sale_price_raw or sale_price_raw == "0":
        return None

    try:
        sold_price = int(float(sale_price_raw.replace(",", "")))
    except (ValueError, TypeError):
        return None
    if sold_price <= 0:
        return None

    year = v.get("modelYear")
    if not year:
        return None
    year = int(year)

    title = v.get("title") or ""
    model = v.get("model") or ""
    search_text = f"{title} {model}"

    model_line  = parse_model_line(search_text)
    generation  = parse_generation(model_line, year, search_text)
    variant     = parse_variant(model_line, year, search_text)

    # Auction date from millisecond timestamp
    end_ts = v.get("auctionEndDate")
    if not end_ts:
        return None
    try:
        sold_date = datetime.fromtimestamp(int(end_ts) / 1000).date()
    except (ValueError, OSError):
        return None

    # Thumbnail: first cloudinary image
    thumb = None
    images = v.get("cloudinaryImages") or []
    if images:
        pid = images[0].get("public_id") or ""
        if pid:
            thumb = f"{CDN_BASE}{urllib.parse.quote(pid, safe='/')}.jpg"

    slug = v.get("slug") or ""
    lot_url = f"{LOT_BASE_URL}{slug}/" if slug else None

    return {
        "make":              "Porsche",
        "model_line":        model_line,
        "generation":        generation,
        "variant":           variant,
        "year":              year,
        "transmission":      "Manual",   # not in API; almost all collector Porsches are manual
        "is_widebody":       None,
        "mileage":           None,
        "thumbnail_url":     thumb,
        "sold_price":        sold_price,
        "auction_source":    "Gooding & Company",
        "auction_url":       lot_url,
        "sold_date":         sold_date,
        "lot_title":         title,
        "exterior_color":    None,
        "paint_to_sample":   parse_paint_to_sample(search_text),
        "production_number": None,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

async def ingest() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.auction_url).where(
                AuctionResult.auction_url.isnot(None),
                AuctionResult.auction_source == "Gooding & Company",
            )
        )
        existing: set[str] = {row[0] for row in rows.fetchall()}

    print(f"Existing Gooding records: {len(existing)}")

    to_insert: list[dict] = []
    total_fetched = total_skipped = 0
    page = 1

    while True:
        try:
            vehicles, nb_pages = fetch_page(page)
        except Exception as exc:
            print(f"  page {page} ERROR: {exc}")
            break

        if not vehicles:
            break

        total_fetched += len(vehicles)
        for v in vehicles:
            rec = map_record(v)
            if rec is None:
                total_skipped += 1
                continue
            url = rec.get("auction_url")
            if url and url in existing:
                total_skipped += 1
                continue
            if url:
                existing.add(url)
            to_insert.append(rec)

        print(f"  page {page}/{nb_pages} — fetched {len(vehicles)}, queued {len(to_insert)} total")

        if page >= nb_pages:
            break
        page += 1
        time.sleep(1)

    async with AsyncSessionLocal() as session:
        if to_insert:
            session.add_all([AuctionResult(**r) for r in to_insert])
            await session.commit()

    print(f"\nDone — fetched: {total_fetched} | inserted: {len(to_insert)} | skipped: {total_skipped}")
    print(f"Database: {DATABASE_PATH}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
