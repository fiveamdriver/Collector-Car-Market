#!/usr/bin/env python3
"""
Ingest Porsche auction results from Mecum Auctions.

Uses the public GraphQL API at https://mecum.stellate.sh (no auth required).
Filters to sold Porsche lots only via taxonomy queries.

Usage (from backend/ directory):
    python data/mecum_ingest.py

Re-running is safe — duplicates are skipped by auction_url.

All key fields come directly from the API:
  hammerPrice  — sold price in USD (integer string, e.g. "22000")
  date         — ISO date string "YYYY-MM-DD"
  odometer     — mileage value, odometerUnits "M" (miles) or "K" (km)
  color        — specific Porsche color name ("Moonlight Blue", "Guards Red")
  transmission — human-readable ("6-Speed Manual", "Automatic")
"""
import asyncio
import json
import os
import re
import ssl
import sys
import time
import urllib.request

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.config import DATABASE_PATH
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from app.utils.color_parser import parse_color_from_phrase, scan_for_color
from datetime import datetime
from sqlalchemy import select

import certifi
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

GRAPHQL_URL = "https://mecum.stellate.sh"
LOT_BASE    = "https://www.mecum.com/lots"
PAGE_SIZE   = 100

# ── GraphQL client ────────────────────────────────────────────────────────────

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


LOTS_QUERY = """
query PorscheSoldLots($size: Int!, $offset: Int!) {
  lots(first: $size, where: {
    taxQuery: {
      relation: AND
      taxArray: [
        { taxonomy: MAKE,        field: SLUG, terms: "porsche", operator: IN }
        { taxonomy: SALERESULT,  field: SLUG, terms: "sold",    operator: IN }
      ]
    }
    offsetPagination: { size: $size, offset: $offset }
  }) {
    pageInfo { offsetPagination { total } }
    edges {
      node {
        title
        slug
        hammerPrice
        date
        odometer
        odometerUnits
        color
        transmission
        vinSerial
        lotNumber
        makes        { nodes { name } }
        models       { nodes { name } }
        lotYears     { nodes { name } }
        trimSubModels { nodes { name } }
        images { url category }
        link
        runDates { nodes { name } }
      }
    }
  }
}
"""


# ── Generation helpers ────────────────────────────────────────────────────────

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

PORSCHE_MODEL_LINES = [
    ("918 Spyder", "918 Spyder"),
    ("959",         "959"),
    ("Cayenne",     "Cayenne"),
    ("Panamera",    "Panamera"),
    ("Macan",       "Macan"),
    ("Taycan",      "Taycan"),
    ("Boxster",     "Boxster"),
    ("Cayman",      "Cayman"),
    ("968",         "968"),
    ("944",         "944"),
    ("930",         "911"),
    ("928",         "928"),
    ("924",         "924"),
    ("914",         "914"),
    ("912E",        "912"),
    ("912",         "912"),
    ("356",         "356"),
    ("904",         "904"),
    ("962",         "962"),
    ("956",         "956"),
    ("935",         "935"),
    ("934",         "934"),
    ("917",         "917"),
    ("908",         "908"),
    ("907",         "907"),
    ("906",         "906"),
    ("Carrera GT",  "Carrera GT"),
    ("911",         "911"),
]

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

_356_VARIANTS = ["Speedster", "Roadster", "Cabriolet", "Coupe", "Notchback"]
_944_VARIANTS = ["Turbo S", "Turbo", "S2", "S"]
_924_VARIANTS = ["Carrera GT", "Carrera GTS", "Turbo"]

YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')


def parse_model_line(text: str) -> str:
    for token, ml in PORSCHE_MODEL_LINES:
        if token == "Carrera GT":
            if re.search(r'\bCarrera GT\b', text): return ml
        elif token[0].isdigit():
            # Match "356", "356A", "356B", "356C" etc. — Mecum titles use "356B" not "356 B"
            if re.search(r'\b' + re.escape(token) + r'[A-Z]?\b', text): return ml
        elif token in text:
            return ml
    return "911"


# Maps Mecum API model names (from models.nodes) to our model_line values.
_API_MODEL_MAP = {
    "356": "356", "356a": "356", "356b": "356", "356c": "356", "356 pre a": "356",
    "911": "911", "912": "912", "914": "914", "918": "918 Spyder", "918 spyder": "918 Spyder",
    "924": "924", "928": "928", "930": "911", "944": "944", "959": "959",
    "962": "962", "968": "968",
    "boxster": "Boxster", "cayman": "Cayman", "carrera gt": "Carrera GT",
    "cayenne": "Cayenne", "macan": "Macan", "panamera": "Panamera", "taycan": "Taycan",
    "917": "917", "906": "906", "907": "907", "908": "908", "904": "904",
    "934": "934", "935": "935", "956": "956",
}


def resolve_model_line(api_models: list[str], title: str) -> str | None:
    if api_models:
        for m in api_models:
            key = m.lower().strip()
            # Exact match first
            if key in _API_MODEL_MAP:
                return _API_MODEL_MAP[key]
            # Prefix match: "911 S" → "911", "Boxster RS 60" → "Boxster"
            for prefix, ml in _API_MODEL_MAP.items():
                if key.startswith(prefix + " ") or key.startswith(prefix + "-"):
                    return ml
        # api_models present but none recognized — non-car (tractor, etc.)
        return None
    return parse_model_line(title)


def parse_generation(model_line: str, year: int, text: str) -> str:
    if model_line == "911":      return get_911_generation(year)
    if model_line == "Cayman":   return get_cayman_generation(year)
    if model_line == "Boxster":  return get_boxster_generation(year)
    if model_line == "356":
        if year <= 1955: return "Pre-A"
        if year <= 1959: return "356 A"
        if year <= 1963: return "356 B"
        return "356 C"
    if model_line == "944":
        if "Turbo" in text: return "944 Turbo"
        if "S2" in text:    return "944 S2"
        return "944"
    return model_line


def parse_variant(model_line: str, year: int, text: str, trim: str) -> str:
    # Prefer trimSubModel from API over title parsing when available
    combined = f"{text} {trim}".strip()

    if model_line == "911":
        gen = get_911_generation(year)
        if gen == "G-Body":
            if "Slant Nose" in combined:                return "Turbo 3.3 Slant Nose"
            if "MFI" in combined:                       return "Carrera 2.7 MFI"
            if "Carrera 2.7" in combined:               return "Carrera 2.7"
            if "Carrera RS 3.0" in combined:            return "Carrera RS 3.0"
            if "Carrera RS" in combined:                return "Carrera RS 2.7"
            if "Speedster" in combined:                 return "Speedster"
            if "Turbo" in combined or "930" in combined: return "930 Turbo"
            if "Targa" in combined:                     return "Targa"
            if "Carrera" in combined and year <= 1977:  return "Carrera 2.7"
            if "SC" in combined:                        return "SC"
            if "Carrera 3.2" in combined or ("Carrera" in combined and year >= 1984):
                                                        return "Carrera 3.2"
            if "911S" in combined or "911 S" in combined: return "911S"
            return "base"
        if gen == "F-Body":
            if "Carrera RS 2.7" in combined or "Carrera RS" in combined: return "Carrera RS 2.7"
            if "Carrera 2.7" in combined: return "Carrera 2.7"
            if "911S" in combined:        return "911S"
            if "Targa" in combined:       return "Targa"
            return "base"
        for pat in _911_VARIANTS:
            if pat in combined: return pat
        return "base"

    if model_line == "356":
        for pat in _356_VARIANTS:
            if pat in combined: return pat
        return "base"

    if model_line == "944":
        for pat in _944_VARIANTS:
            if pat in combined: return pat
        return "base"

    if model_line == "924":
        for pat in _924_VARIANTS:
            if pat in combined: return pat
        return "base"

    if model_line in ("Cayman", "Boxster"):
        for pat in ["GT4 RS", "GT4", "GTS", "Spyder RS", "Spyder"]:
            if pat in combined: return pat
        if re.search(r'\bR\b', combined): return "R"
        if re.search(r'\bS\b', combined): return "S"
        return "base"

    return "base"


# ── Field parsers ─────────────────────────────────────────────────────────────

def parse_transmission(raw: str | None) -> str:
    if not raw:
        return "Manual"
    return "Automatic" if "automatic" in raw.lower() else "Manual"


def parse_odometer(value: str | None, units: str | None) -> int | None:
    if not value:
        return None
    try:
        miles = float(value.replace(",", ""))
    except (ValueError, TypeError):
        return None
    if (units or "").upper() in ("K", "KM", "KMT"):
        miles = miles / 1.609
    result = round(miles)
    return result if result >= 100 else None


def parse_color(raw: str | None) -> str | None:
    if not raw or raw.lower() in ("", "other", "multicolor", "two tone"):
        return None
    known = scan_for_color(raw)
    if known:
        return known
    return parse_color_from_phrase(raw)


def parse_pts(title: str, color: str | None) -> bool | None:
    if re.search(r'paint[-\s]to[-\s]sample|\bPTS\b', title, re.IGNORECASE):
        return True
    if color and re.search(r'paint[-\s]to[-\s]sample|\bPTS\b', color, re.IGNORECASE):
        return True
    return None


# ── Record mapper ─────────────────────────────────────────────────────────────

def map_record(node: dict) -> dict | None:
    title = node.get("title") or ""

    # Year
    years = [y["name"] for y in (node.get("lotYears") or {}).get("nodes", [])]
    if not years:
        m = YEAR_RE.search(title)
        year_str = m.group() if m else None
    else:
        year_str = years[0]
    if not year_str:
        return None
    try:
        year = int(year_str)
    except ValueError:
        return None

    # Price
    hammer = node.get("hammerPrice") or ""
    try:
        sold_price = int(str(hammer).replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return None
    if sold_price <= 0:
        return None

    # Date — use runDates (actual auction date), not `date` (CMS timestamp)
    run_nodes = (node.get("runDates") or {}).get("nodes", [])
    date_str = run_nodes[0]["name"][:10] if run_nodes else ""
    try:
        sold_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, IndexError, KeyError):
        return None

    # Model
    trim_nodes  = (node.get("trimSubModels") or {}).get("nodes", [])
    trim        = " ".join(t["name"] for t in trim_nodes)
    api_models  = [m["name"] for m in (node.get("models") or {}).get("nodes", [])]
    model_line  = resolve_model_line(api_models, title)
    if model_line is None:
        return None
    generation  = parse_generation(model_line, year, title)
    variant    = parse_variant(model_line, year, title, trim)

    # Mileage
    mileage    = parse_odometer(node.get("odometer"), node.get("odometerUnits"))

    # Color
    color_raw  = node.get("color") or ""
    color      = parse_color(color_raw)
    pts        = parse_pts(title, color_raw)

    # Thumbnail — first exterior image from images list
    images_list = node.get("images") or []
    thumbnail = next(
        (img["url"] for img in images_list if img.get("category") == "Exterior"),
        None,
    )

    # URL — use `link` field (includes numeric DB id: /lots/1161580/slug/)
    lot_url = node.get("link") or None

    return {
        "make":              "Porsche",
        "model_line":        model_line,
        "generation":        generation,
        "variant":           variant,
        "year":              year,
        "transmission":      parse_transmission(node.get("transmission")),
        "is_widebody":       None,
        "mileage":           mileage,
        "thumbnail_url":     thumbnail,
        "sold_price":        sold_price,
        "auction_source":    "Mecum",
        "auction_url":       lot_url,
        "sold_date":         sold_date,
        "lot_title":         title,
        "exterior_color":    color,
        "paint_to_sample":   pts,
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
                AuctionResult.auction_source == "Mecum",
            )
        )
        existing: set[str] = {row[0] for row in rows.fetchall()}

    print(f"Existing Mecum records: {len(existing)}")

    to_insert: list[dict] = []
    total_seen = 0
    offset     = 0
    total      = None

    while True:
        try:
            resp = gql(LOTS_QUERY, {"size": PAGE_SIZE, "offset": offset})
        except Exception as exc:
            print(f"  offset={offset} ERROR: {exc}")
            break

        if "errors" in resp:
            print(f"  GraphQL errors: {resp['errors']}")
            break

        data   = resp["data"]["lots"]
        edges  = data.get("edges") or []
        if total is None:
            total = (data.get("pageInfo") or {}).get("offsetPagination", {}).get("total", 0)

        if not edges:
            break

        total_seen += len(edges)

        for edge in edges:
            node    = edge["node"]
            lot_url = node.get("link") or None

            if lot_url and lot_url in existing:
                continue

            rec = map_record(node)
            if rec is None:
                continue

            if lot_url:
                existing.add(lot_url)
            to_insert.append(rec)

        page_num = offset // PAGE_SIZE + 1
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE if total else "?"
        print(
            f"  page {page_num}/{total_pages} (offset={offset}) — "
            f"{len(edges)} lots, {len(to_insert)} queued"
        )

        if len(edges) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.5)

    async with AsyncSessionLocal() as session:
        if to_insert:
            session.add_all([AuctionResult(**r) for r in to_insert])
            await session.commit()

    print(
        f"\nDone — total seen: {total_seen} | inserted: {len(to_insert)} | "
        f"skipped (existing): {total_seen - len(to_insert)}"
    )
    print(f"Database: {DATABASE_PATH}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
