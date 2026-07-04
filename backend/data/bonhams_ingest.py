#!/usr/bin/env python3
"""
Ingest Porsche auction results from Bonhams|Cars (cars.bonhams.com).

Bonhams runs a Next.js site backed by a Typesense search cluster.  The site's
runtime config exposes a public, search-only Typesense API key, and the `lots`
collection is directly queryable — no Playwright / headless browser needed
(unlike broad_arrow_ingest.py).  We query the collection for "porsche", keep
only the Cars department and SOLD lots, and page through the results.

Usage (from backend/ directory):
    python data/bonhams_ingest.py

Re-running is safe — duplicates are skipped by auction_url.

Price:   price.hammerPremium (hammer + buyer's premium), in the lot's local
         currency, converted to USD via FX_RATES to match the other sources
         (Gooding / RM store the premium-inclusive realized price).
Date:    hammerTime.datetime (exact sale timestamp).
Mileage: not a structured field — left NULL (backfill later if needed).
Color:   not a structured field — left NULL (backfill later if needed).

The Typesense key is scraped fresh from the results page each run (it rotates
on deploy); TYPESENSE_KEY_FALLBACK is used if the scrape fails.
"""
import json
import os
import re
import ssl
import sys
import urllib.request
from datetime import date, datetime

import certifi

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.config import DATABASE_URL
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from sqlalchemy import select
import asyncio

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

RESULTS_PAGE       = "https://cars.bonhams.com/auctions/results/"
TYPESENSE_HOST     = "https://api01.bonhams.com"
TYPESENSE_PATH     = "/search-proxy/multi_search?use_cache=true"
TYPESENSE_KEY_FALLBACK = "7YZqOyG0twgst4ACc2VuCyZxpGAYzM0weFTLCC20FQY"
LOT_URL_BASE       = "https://cars.bonhams.com/auction"
PAGE_SIZE          = 250
UA                 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/131.0.0.0 Safari/537.36")

# MOT-CAR = the "Cars" department (excludes Automobilia, Motorcycles, Watches,
# and other memorabilia that also match a "porsche" text query).
CAR_DEPT_CODE = "MOT-CAR"

# Local currency → USD.  Bonhams sells in USD/EUR/GBP/CHF; approximate
# mid-market rates.  Update periodically for accuracy on recent sales.
FX_RATES: dict[str, float] = {
    "USD": 1.00,
    "EUR": 1.09,
    "GBP": 1.27,
    "CHF": 1.13,
}


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


# Bonhams titles read "<year> Porsche <model> <details> Chassis no. <x> Engine
# no. <y> ...".  The model designation always sits up front; the trailing
# chassis / engine / registration numbers are digit-soup that false-matches
# numeric model codes (e.g. "Engine no. 907 672" looks like a 907).  Strip from
# the first identifier keyword onward before parsing the model line.
_IDENTIFIER_RE = re.compile(
    r'\b(?:chassis|engine|gearbox|frame|registration|reg\.?|body|coachwork)\b'
    r'|\bVIN\b|\bno\.\s*\d',
    re.IGNORECASE,
)


def descriptive_part(title: str) -> str:
    m = _IDENTIFIER_RE.search(title)
    return title[:m.start()] if m else title


def parse_model_line(text: str) -> str:
    # 356 and its sub-series (356A/356B/356C/356SC — the suffix is often attached,
    # e.g. "356A", "356SC").  Checked first so it beats "Carrera GT": a 356 Carrera
    # GT is a 356, not the 2003-07 Carrera GT supercar.  Requiring 356 to be flanked
    # by non-digits keeps it from matching "356" buried in a chassis/engine number.
    if re.search(r'(?<!\d)356(?!\d)', text):
        return "356"
    # The 906 is marketed as the "Carrera 6" / "Carrera Six"; some titles use only
    # that name and carry "906" only in the (stripped) chassis number.  The speed
    # guard avoids catching a modern "Carrera 6-speed".
    if re.search(r'\bCarrera[\s\-]?(?:6|Six)\b(?!\s*[-–]?\s*speed)', text, re.IGNORECASE):
        return "906"
    # 918 Spyder hypercar — but NOT the 911 Turbo S "Edition 918 Spyder" trim,
    # which is a 911.  A real 918's title never also carries "911".
    if re.search(r'918\s*Spyder', text, re.IGNORECASE) and not re.search(r'\b911\b', text):
        return "918 Spyder"
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
    return model_line


def parse_variant(model_line: str, year: int, text: str) -> str:
    if model_line == "914":
        return "914/6" if re.search(r'914[/-]6', text) else "base"
    if model_line == "911":
        gen = get_911_generation(year)
        if gen == "G-Body":
            if "Slant Nose" in text:                return "Turbo 3.3 Slant Nose"
            if "MFI" in text:                       return "Carrera 2.7 MFI"
            if "Carrera 2.7" in text:               return "Carrera 2.7"
            if "Carrera RS 3.0" in text:            return "Carrera RS 3.0"
            if "Carrera RS" in text:                return "Carrera RS 2.7"
            if "Speedster" in text:                 return "Speedster"
            if "Turbo" in text or "930" in text:    return "930 Turbo"
            if "Targa" in text:                     return "Targa"
            if "Carrera" in text and year <= 1977:  return "Carrera 2.7"
            if "SC" in text:                        return "SC"
            if "Carrera 3.2" in text or ("Carrera" in text and year >= 1984):
                                                    return "Carrera 3.2"
            if "911S" in text or "911 S" in text:   return "911S"
            return "base"
        if gen == "F-Body":
            if "Carrera RS 2.7" in text or "Carrera RS" in text: return "Carrera RS 2.7"
            if "Carrera 2.7" in text:               return "Carrera 2.7"
            if "911S" in text:                      return "911S"
            if "Targa" in text:                     return "Targa"
            return "base"
        for pat in _911_VARIANTS:
            if pat in text:
                return pat
        return "base"

    if model_line == "356":
        for pat in _356_VARIANTS:
            if pat in text: return pat
        return "base"

    if model_line == "944":
        for pat in _944_VARIANTS:
            if pat in text: return pat
        return "base"

    if model_line == "924":
        for pat in _924_VARIANTS:
            if pat in text: return pat
        return "base"

    if model_line in ("Cayman", "Boxster"):
        for pat in ["GT4 RS", "GT4", "GTS", "Spyder RS", "Spyder"]:
            if pat in text: return pat
        if re.search(r'\bR\b', text): return "R"
        if re.search(r'\bS\b', text): return "S"
        return "base"

    return "base"


# ── Transmission ──────────────────────────────────────────────────────────────

def parse_transmission(text: str) -> str:
    t = text.lower()
    if "pdk" in t:                                        return "PDK"
    if "tiptronic" in t:                                  return "Automatic"
    if "sportomatic" in t:                                return "Automatic"
    if "automatic" in t:                                  return "Automatic"
    return "Manual"


# ── Lot mapper ────────────────────────────────────────────────────────────────

YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')

# A "porsche" text query in the Cars department still catches a few non-cars:
# automobilia (posters, scale models) miscoded MOT-CAR, and Porsche's
# agricultural tractors (real vehicles, but not the collector sports-car market
# this app tracks — and they'd all fall into the 911 fallback bucket).
NON_CAR_RE = re.compile(
    r'\b(poster|posters|scale model|model of|tractor|brochure|painting|'
    r'artwork|sculpture|helmet|\bsign\b|badge|race engine)\b',
    re.IGNORECASE,
)


def build_lot_url(doc: dict) -> str | None:
    auction_id = doc.get("auctionId")
    lot_id     = doc.get("lotId")
    slug       = doc.get("slug") or ""
    if not auction_id or not lot_id:
        return None
    return f"{LOT_URL_BASE}/{auction_id}/lot/{lot_id}/{slug}/"


def map_lot(doc: dict) -> dict | None:
    """Map a Bonhams Typesense lot document to an auction_results row dict."""
    title = (doc.get("title") or "").strip()
    if "porsche" not in title.lower():
        return None
    if NON_CAR_RE.search(title):
        return None

    # Year — first 4-digit year in the title.
    m = YEAR_RE.search(title)
    if not m:
        return None
    year = int(m.group(0))
    if year < 1948 or year > 2030:
        return None

    # Price: premium-inclusive, converted to USD.
    price = doc.get("price") or {}
    local = price.get("hammerPremium") or price.get("hammerPrice")
    if not local or local <= 0:
        return None
    iso = (doc.get("currency") or {}).get("iso_code") or "USD"
    fx  = FX_RATES.get(iso)
    if fx is None:
        return None  # unknown currency — skip rather than store a wrong number
    sold_price = round(float(local) * fx)

    # Sale date from the hammer timestamp.
    sold_date = None
    dt = (doc.get("hammerTime") or {}).get("datetime")
    if dt:
        try:
            sold_date = datetime.fromisoformat(dt.replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            sold_date = None

    lot_url = build_lot_url(doc)
    if not lot_url:
        return None

    desc       = descriptive_part(title)
    model_line = parse_model_line(desc)
    generation = parse_generation(model_line, year, desc)
    variant    = parse_variant(model_line, year, desc)

    image = doc.get("image") or {}
    thumbnail = image.get("url") or None

    return {
        "make":              "Porsche",
        "model_line":        model_line,
        "generation":        generation,
        "variant":           variant,
        "year":              year,
        "transmission":      parse_transmission(title),
        "is_widebody":       None,
        "mileage":           None,       # not a structured field
        "thumbnail_url":     thumbnail,
        "sold_price":        sold_price,
        "auction_source":    "Bonhams",
        "auction_url":       lot_url,
        "sold_date":         sold_date,
        "lot_title":         title,
        "exterior_color":    None,        # not a structured field
        "paint_to_sample":   None,
        "production_number": None,
    }


# ── Typesense fetch ───────────────────────────────────────────────────────────

_KEY_RE = re.compile(r'"search"\s*:\s*"([A-Za-z0-9]{32,})"')


def scrape_typesense_key() -> str:
    """Scrape the current search-only Typesense key from the site config."""
    req = urllib.request.Request(RESULTS_PAGE, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(r'"TYPESENSE"\s*:\s*\{.*?"apiKey"\s*:\s*\{(.*?)\}', html)
        if m:
            km = _KEY_RE.search(m.group(1))
            if km:
                return km.group(1)
    except Exception as exc:
        print(f"  key scrape failed ({exc}); using fallback")
    return TYPESENSE_KEY_FALLBACK


def fetch_page(key: str, page: int) -> tuple[list[dict], int]:
    """Return (lot_documents, total_found) for a 1-based page of SOLD car lots."""
    body = json.dumps({
        "searches": [{
            "collection": "lots",
            "q":          "porsche",
            "query_by":   "title",
            "filter_by":  f"department.code:{CAR_DEPT_CODE} && status:SOLD",
            "per_page":   PAGE_SIZE,
            "page":       page,
        }]
    }).encode()
    req = urllib.request.Request(
        TYPESENSE_HOST + TYPESENSE_PATH, data=body, method="POST",
        headers={
            "Content-Type":      "application/json",
            "x-typesense-api-key": key,
            "User-Agent":        UA,
        },
    )
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
        payload = json.loads(resp.read().decode())
    result = payload["results"][0]
    if result.get("error"):
        raise RuntimeError(f"Typesense error: {result['error']}")
    docs = [h["document"] for h in result.get("hits", [])]
    return docs, result.get("found", 0)


# ── Main ──────────────────────────────────────────────────────────────────────

async def ingest() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(AuctionResult.auction_url).where(
                AuctionResult.auction_url.isnot(None),
                AuctionResult.auction_source == "Bonhams",
            )
        )
        existing: set[str] = {row[0] for row in rows.fetchall()}

    print(f"Existing Bonhams records: {len(existing)}")

    key = scrape_typesense_key()

    to_insert:  list[dict] = []
    total_seen = 0
    page       = 1
    total_found = None

    while True:
        docs, found = fetch_page(key, page)
        if total_found is None:
            total_found = found
            print(f"Total SOLD Porsche car lots reported: {found}")
        if not docs:
            break

        total_seen += len(docs)
        for doc in docs:
            rec = map_lot(doc)
            if rec is None:
                continue
            url = rec["auction_url"]
            if url in existing:
                continue
            existing.add(url)
            to_insert.append(rec)

        print(f"  page {page} — {len(docs)} lots seen, {len(to_insert)} queued total")

        if total_seen >= (total_found or 0) or len(docs) < PAGE_SIZE:
            break
        page += 1

    async with AsyncSessionLocal() as session:
        if to_insert:
            session.add_all([AuctionResult(**r) for r in to_insert])
            await session.commit()

    print(
        f"\nDone — pages: {page} | lots seen: {total_seen} | "
        f"inserted: {len(to_insert)} | skipped (existing/non-Porsche): "
        f"{total_seen - len(to_insert)}"
    )
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
