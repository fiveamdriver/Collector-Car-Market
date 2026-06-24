#!/usr/bin/env python3
"""
Ingest Porsche race car listings from Race Cars For You (racecarsforyou.com).

These are sold classifieds listings, not confirmed auction results.
- sold_price is set to the asking price when shown, or NULL when hidden
- sold_date is always NULL (site does not publish when cars sold)

Usage (from backend/ directory):
    python data/rcfy_ingest.py

Re-running is safe — duplicates are skipped by auction_url.
"""
import asyncio
import certifi
import re
import ssl
import sys
import time
import os
import urllib.request

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.config import DATABASE_PATH
from app.database import AsyncSessionLocal, Base, engine
from app.models.listing import AuctionResult
from sqlalchemy import select

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

BASE_URL    = "https://racecarsforyou.com"
SEARCH_URL  = (
    BASE_URL
    + "/search-for-race-cars/"
    + "?_listing_type=race-car&_listing_status=sold&_make=porsche"
    + "&_currency=undefined&_paged={page}"
)
SOURCE      = "Race Cars For You"
RATE_LIMIT  = 1.2  # seconds between requests
UA          = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


# ── HTTP ─────────────────────────────────────────────────────────────────────

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    with urllib.request.urlopen(req, context=SSL_CTX) as resp:
        raw = resp.read()
    import gzip
    try:
        return gzip.decompress(raw).decode("utf-8", errors="replace")
    except Exception:
        return raw.decode("utf-8", errors="replace")


# ── Generation lookups ────────────────────────────────────────────────────────

def get_911_generation(year: int) -> str:
    if year <= 1973: return "F-Body"
    if year <= 1989: return "G-Body"
    if year <= 1994: return "964"
    if year <= 1998: return "993"
    if year <= 2005: return "996"
    if year <= 2012: return "997"
    if year <= 2019: return "991"
    return "992"


def get_cayman_generation(year: int) -> str:
    if year <= 2008: return "987.1"
    if year <= 2012: return "987.2"
    if year <= 2016: return "981"
    return "718"


# ── Classification ────────────────────────────────────────────────────────────

def classify(title: str, year: int) -> tuple[str, str, str]:
    """Return (model_line, generation, variant) for a race car listing title."""
    t = title

    # ── 718 Clubsport (non-GT4 track variant) ────────────────────────────────
    if re.search(r'718.*Clubsport|Clubsport.*718', t, re.I) and not re.search(r'GT4', t, re.I):
        gen = get_cayman_generation(year)
        mr = bool(re.search(r'\bMR\b', t))
        return ("Cayman Race", gen, "GT4 Clubsport MR" if mr else "GT4 Clubsport")

    # ── 911 GT3 Cup ──────────────────────────────────────────────────────────
    # "Cup Car" requires 911/GT3 context; "Carrera Cup" and "NNN Cup" match by chassis gen
    is_gt3_cup = bool(re.search(r'GT3\s*Cup|GT3R\b', t, re.I))
    is_cup_car = bool(re.search(r'Cup\s*Car', t, re.I)) and bool(re.search(r'\b(?:911|991|992|997|996|993|964)\b', t))
    is_carrera_cup = bool(re.search(r'Carrera\s+Cup', t, re.I))
    is_chassis_cup = bool(re.search(r'\b(?:992|991|997\.?2?|996)(?:\.\d)?\s+Cup\b', t, re.I))
    if is_gt3_cup or is_cup_car or is_carrera_cup or is_chassis_cup:
        gen = get_911_generation(year)
        return ("911 Race", gen, "GT3 Cup")

    # ── 911 GT3 R (customer racing GT3R) ─────────────────────────────────────
    if re.search(r'\bGT3\s*R\b', t, re.I) and (re.search(r'\b911\b', t) or year >= 2010):
        gen = get_911_generation(year)
        return ("911 Race", gen, "GT3 R")

    # ── 911 GT2 RS Clubsport ─────────────────────────────────────────────────
    if re.search(r'GT2\s*RS', t, re.I):
        gen = get_911_generation(year)
        return ("911 Race", gen, "GT2 RS Clubsport")

    # ── RSR ──────────────────────────────────────────────────────────────────
    if re.search(r'\bRSR\b', t) and re.search(r'\b911\b', t):
        gen = get_911_generation(year)
        if re.search(r'GT3.*RSR', t, re.I):
            return ("911 Race", gen, "GT3 RSR")
        return ("911 Race", gen, "RSR")

    # ── GT4 Clubsport (718 Cayman / 981 Cayman) ──────────────────────────────
    if re.search(r'GT4\s*(?:RS\s*)?Clubsport|GT4\s*RS\b', t, re.I):
        gen = get_cayman_generation(year)
        if re.search(r'GT4\s*RS', t, re.I):
            return ("Cayman Race", gen, "GT4 RS Clubsport")
        if re.search(r'\bMR\b', t):
            return ("Cayman Race", gen, "GT4 Clubsport MR")
        return ("Cayman Race", gen, "GT4 Clubsport")

    # ── 718 GT4 (generic) ────────────────────────────────────────────────────
    if re.search(r'718.*GT4|GT4.*718', t, re.I):
        return ("Cayman Race", "718", "GT4 Clubsport")

    # ── Cayman GT4 (pre-718) ─────────────────────────────────────────────────
    if re.search(r'Cayman.*GT4|GT4.*Cayman', t, re.I):
        gen = get_cayman_generation(year)
        return ("Cayman Race", gen, "GT4 Clubsport")

    # ── Boxster race variants ─────────────────────────────────────────────────
    if re.search(r'Boxster', t, re.I) and re.search(r'track|race|cup|club', t, re.I):
        return ("Boxster", "986", "base")

    # ── Historic standalone race cars ─────────────────────────────────────────
    for model_num, ml in [("917", "917"), ("962", "962"), ("956", "956"),
                           ("935", "935"), ("934", "934"), ("908", "908"),
                           ("906", "906"), ("904", "904"), ("550", "550")]:
        if re.search(r'\b' + model_num + r'\b', t):
            return (ml, ml, "base")

    if re.search(r'RS Spyder', t, re.I):
        return ("RS Spyder", "RS Spyder", "base")

    # ── Generic 911 race car ──────────────────────────────────────────────────
    if re.search(r'\b911\b', t):
        gen = get_911_generation(year)
        return ("911 Race", gen, "base")

    # ── Targa Silhouette / odd builds ─────────────────────────────────────────
    if re.search(r'Targa', t, re.I):
        return ("911", get_911_generation(year), "Targa")

    return ("911 Race", get_911_generation(year), "base")


# ── HTML parsing ──────────────────────────────────────────────────────────────

def _strip(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


def parse_listing_page(html: str, url: str) -> dict | None:
    """Parse a single listing detail page. Returns None if not Porsche/sold."""

    # Must be sold
    if not re.search(r'listing-sold', html):
        return None

    # Title
    h1 = re.search(r'<h1[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h1>', html, re.S)
    if not h1:
        return None
    title = _strip(h1.group(1))

    # Strip style/script blocks before further parsing
    body = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.S)
    body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.S)

    # Structured detail fields: <div class="detail-label">Year</div><div class="detail-value">2018</div>
    def detail(label: str) -> str | None:
        m = re.search(
            r'<div[^>]*detail-label[^>]*>\s*' + re.escape(label) + r'\s*</div>\s*'
            r'<div[^>]*detail-value[^>]*>(.*?)</div>',
            body, re.S | re.I,
        )
        return _strip(m.group(1)) if m else None

    year_str = detail("Year")
    if not year_str or not year_str.isdigit():
        return None
    year = int(year_str)
    if year < 1950 or year > 2030:
        return None

    # Engine / transmission / chassis hours
    def hours(label: str) -> str | None:
        m = re.search(
            r'<div[^>]*detail-label[^>]*>\s*' + re.escape(label) + r'\s*</div>\s*'
            r'<div[^>]*detail-value[^>]*>(.*?)</div>',
            body, re.S | re.I,
        )
        return _strip(m.group(1)) if m else None

    engine_hrs  = hours("Engine Hours")
    trans_hrs   = hours("Transmission Hours")
    chassis_hrs = hours("Chassis Hours")

    # Asking price — first monetary value in the main listing block.
    # We stop before "Related Listings" to avoid picking up sidebar cards.
    related_idx = body.find("Related Listings")
    price_body  = body[:related_idx] if related_idx > 0 else body
    # Match $X,XXX or €X,XXX — require >$5k to skip small deposits/fees
    price_m = re.search(
        r'[\$€£]([\d,]+)',
        price_body,
    )
    asking_price = None
    if price_m:
        val = int(price_m.group(1).replace(',', ''))
        if val >= 5_000:
            asking_price = val

    # Thumbnail — first preloaded image
    thumb_m = re.search(r"<link[^>]+rel=['\"]preload['\"][^>]+as=['\"]image['\"][^>]+href=['\"]([^'\"]+)['\"]", html)
    if not thumb_m:
        thumb_m = re.search(r"href=['\"]([^'\"]+\.jpg)['\"]", html)
    thumbnail = thumb_m.group(1) if thumb_m else None

    # VIN / chassis
    vin_m = re.search(r'\bVIN[:\s]+([A-Z0-9]{10,17})\b', body, re.I)
    vin   = vin_m.group(1) if vin_m else None

    model_line, generation, variant = classify(title, year)

    # Build a descriptive lot_title with available hours
    hours_parts = []
    if engine_hrs:  hours_parts.append(f"{engine_hrs} engine hrs")
    if trans_hrs:   hours_parts.append(f"{trans_hrs} trans hrs")
    if chassis_hrs: hours_parts.append(f"{chassis_hrs} chassis hrs")
    hours_str = " · ".join(hours_parts)
    lot_title = f"{title}  [{hours_str}]" if hours_str else title

    return {
        "lot_title":     lot_title,
        "year":          year,
        "make":          "Porsche",
        "model_line":    model_line,
        "generation":    generation,
        "variant":       variant,
        "transmission":  "PDK" if year >= 2009 else "Manual",  # reasonable default for Cup cars
        "sold_price":    asking_price,
        "sold_date":     None,
        "auction_source": SOURCE,
        "auction_url":   url,
        "thumbnail_url": thumbnail,
        "mileage":       None,
    }


def get_listing_urls_from_page(html: str) -> list[str]:
    links = re.findall(
        r'href="(https://racecarsforyou\.com/listing/[^"]+)"',
        html,
    )
    return list(dict.fromkeys(links))  # dedupe, preserve order


# ── DB helpers ────────────────────────────────────────────────────────────────

async def load_existing_urls(session) -> set[str]:
    rows = await session.execute(
        select(AuctionResult.auction_url).where(
            AuctionResult.auction_source == SOURCE
        )
    )
    return {r[0] for r in rows.all() if r[0]}


async def insert_record(session, data: dict) -> None:
    rec = AuctionResult(**data)
    session.add(rec)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        existing_urls = await load_existing_urls(session)

    print(f"Database: {DATABASE_PATH}")
    print(f"Existing Race Cars For You records: {len(existing_urls)}")

    all_listing_urls: list[str] = []

    page = 1
    while True:
        url = SEARCH_URL.format(page=page)
        print(f"\nFetching page {page} …", end=" ", flush=True)
        html = fetch(url)
        links = get_listing_urls_from_page(html)
        if not links:
            print("no listings found — done paginating.")
            break
        new_links = [l for l in links if l not in existing_urls]
        all_listing_urls.extend(new_links)
        print(f"{len(links)} listings ({len(new_links)} new)")
        page += 1
        time.sleep(RATE_LIMIT)

    print(f"\n{len(all_listing_urls)} new listings to fetch.")

    inserted = 0
    skipped  = 0

    async with AsyncSessionLocal() as session:
        for i, listing_url in enumerate(all_listing_urls, 1):
            print(f"  [{i}/{len(all_listing_urls)}] {listing_url}", end=" … ", flush=True)
            try:
                html = fetch(listing_url)
                data = parse_listing_page(html, listing_url)
                if data is None:
                    print("skipped (not sold / not Porsche)")
                    skipped += 1
                else:
                    await insert_record(session, data)
                    price_str = f"${data['sold_price']:,}" if data['sold_price'] else "no price"
                    print(f"{data['year']} {data['model_line']} {data['variant']} — {price_str}")
                    inserted += 1
            except Exception as exc:
                print(f"ERROR: {exc}")
                skipped += 1
            time.sleep(RATE_LIMIT)

        await session.commit()

    print(f"\n── Summary ──────────────────────────────────────────────────────")
    print(f"Inserted : {inserted}")
    print(f"Skipped  : {skipped}")
    print(f"Database : {DATABASE_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
