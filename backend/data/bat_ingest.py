#!/usr/bin/env python3
"""
Ingest Porsche auction data from BaT's internal API into auction_results.

Usage (from backend/ directory):
    python data/bat_ingest.py

No API key required. Re-running is safe — duplicates are skipped by auction_url.
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
from datetime import date, datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import Base
from app.models.listing import AuctionResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(BACKEND_DIR, 'pcarmarket.db')}"
engine       = create_async_engine(DATABASE_URL)
AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

API_URL   = "https://bringatrailer.com/wp-json/bringatrailer/1.0/data/listings-filter"
SSL_CTX   = ssl.create_default_context(cafile=certifi.where())
MAX_PAGES = None  # set to an integer to limit pages per config during test runs


# ── Query configs ─────────────────────────────────────────────────────────────

CONFIGS = [
    {"name": "911 GT3/GT3 RS",    "ids": [2015688, 55778434, 55778221, 55778351], "model_line": "911",        "variant": "GT3"},
    {"name": "993",               "ids": [1833039],                               "model_line": "911",        "variant": None},
    {"name": "964",               "ids": [1833038],                               "model_line": "911",        "variant": None},
    {"name": "964 Carrera RS",    "ids": [74679063],                              "model_line": "911",        "variant": "Carrera RS"},
    {"name": "Carrera GT",        "ids": [38349021],                              "model_line": "Carrera GT", "variant": "base"},
    {"name": "959",               "ids": [39491899],                              "model_line": "959",        "variant": "base"},
    {"name": "918 Spyder",        "ids": [38553278],                              "model_line": "918 Spyder", "variant": None},
    {"name": "991 R",             "ids": [107021997],                             "model_line": "911",        "variant": "R"},
    {"name": "992 S/T",           "ids": [106842163],                             "model_line": "911",        "variant": "S/T"},
    {"name": "993 GT2",           "ids": [55777633],                              "model_line": "911",        "variant": "GT2"},
    {"name": "997 Sport Classic", "ids": [107031857],                             "model_line": "911",        "variant": "Sport Classic"},
    {"name": "991 Speedster",     "ids": [107022050],                             "model_line": "911",        "variant": "Speedster"},
    {"name": "930 Turbo",         "ids": [1833042],                               "model_line": "911",        "variant": "Turbo 3.3"},
    {"name": "996 Turbo",         "ids": [1833045],                               "model_line": "911",        "variant": "Turbo"},
    {"name": "992 Turbo",         "ids": [40033130],                              "model_line": "911",        "variant": "Turbo"},
    {"name": "911 SC",            "ids": [16982431],                              "model_line": "911",        "variant": "SC"},
    {"name": "911 Carrera 3.2",   "ids": [1833037],                               "model_line": "911",        "variant": "Carrera 3.2"},
    {"name": "Carrera RS 2.7",    "ids": [68399612],                              "model_line": "911",        "variant": "Carrera RS 2.7"},
]


# ── Generation lookup ─────────────────────────────────────────────────────────

def get_911_generation(year: int) -> str:
    if year <= 1973: return "F-Series"
    if year <= 1989: return "G-Series"
    if year <= 1994: return "964"
    if year <= 1998: return "993"
    if year <= 2001: return "996.1"
    if year <= 2005: return "996.2"
    if year <= 2008: return "997.1"
    if year <= 2012: return "997.2"
    if year <= 2016: return "991.1"
    if year <= 2019: return "991.2"
    return "992"


# ── Field parsers ─────────────────────────────────────────────────────────────

YEAR_RE     = re.compile(r'\b(19|20)\d{2}\b')
MILEAGE_RE  = re.compile(r'([\d,]+)(k)?-(Mile|Kilometer)', re.IGNORECASE)

VARIANT_PATTERNS = [
    "GT3 RS 4.0", "GT3 RS", "GT3",
    "GT2 RS", "GT2",
    "Turbo S", "Turbo",
    "Carrera RS", "Carrera S", "Carrera GTS", "Carrera T", "Carrera",
]

WIDEBODY_VARIANTS = {"GT3 RS", "GT3 RS 4.0", "GT2", "GT2 RS", "Turbo", "Turbo S", "Turbo 3.3", "Turbo 3.0"}
WIDEBODY_MODELS   = {"959", "Carrera GT", "918 Spyder"}


def parse_year(title: str) -> int | None:
    m = YEAR_RE.search(title)
    return int(m.group()) if m else None


def parse_variant(title: str) -> str:
    for pat in VARIANT_PATTERNS:
        if pat in title:
            return pat
    return "base"


def parse_transmission(title: str) -> str:
    if any(k in title for k in ("6-Speed", "6-speed", "Manual")):
        return "manual"
    if any(k in title for k in ("PDK", "7-Speed")):
        return "pdk"
    return "manual"


def parse_mileage(title: str) -> int | None:
    m = MILEAGE_RE.search(title)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    if m.group(2):                              # 'k' suffix
        value *= 1_000
    if "kilometer" in m.group(3).lower():
        value /= 1.609
    return round(value)


def parse_paint_to_sample(title: str) -> bool | None:
    if re.search(r'paint[-\s]to[-\s]sample|PTS', title, re.IGNORECASE):
        return True
    return None


def compute_is_widebody(variant: str, model_line: str) -> bool:
    # Not stored in DB schema — computed here for future use / logging
    return variant in WIDEBODY_VARIANTS or model_line in WIDEBODY_MODELS


# ── API fetch ─────────────────────────────────────────────────────────────────

def fetch_page(ids: list[int], page: int) -> list[dict]:
    params = [
        ("page",                     page),
        ("per_page",                 24),
        ("get_items",                1),
        ("get_stats",                0),
        ("base_filter[items_type]",  "model"),
        ("sort",                     "td"),
    ]
    for id_ in ids:
        params.append(("base_filter[keyword_pages][]", id_))

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "Accept":     "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
        payload = json.loads(resp.read().decode())
    return payload.get("items") or []


# ── Record mapper ─────────────────────────────────────────────────────────────

def map_record(raw: dict, model_line: str, config_variant: str | None) -> dict | None:
    sold_text = raw.get("sold_text") or ""
    if not sold_text.startswith("Sold for"):
        return None

    price = raw.get("current_bid")
    if price is None:
        return None

    title = raw.get("title") or ""
    year  = parse_year(title)
    if not year:
        return None

    variant      = config_variant if config_variant is not None else parse_variant(title)
    generation   = get_911_generation(year) if model_line == "911" else model_line
    transmission = parse_transmission(title)

    ts = raw.get("sold_text_timestamp")
    try:
        sold_date = datetime.fromtimestamp(int(ts)).date()
    except (TypeError, ValueError, OSError):
        sold_date = date.today()

    return dict(
        make              = "Porsche",
        model_line        = model_line,
        generation        = generation,
        variant           = variant,
        year              = year,
        transmission      = transmission,
        is_widebody       = compute_is_widebody(variant, model_line) or None,
        mileage           = parse_mileage(title),
        color             = None,
        sold_price        = int(price),
        auction_source    = "BaT",
        auction_url       = raw.get("url"),
        sold_date         = sold_date,
        lot_title         = title,
        paint_to_sample   = parse_paint_to_sample(title),
        production_number = None,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

async def ingest() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession() as session:
        rows = await session.execute(
            select(AuctionResult.auction_url).where(
                AuctionResult.auction_url.isnot(None)
            )
        )
        existing_urls: set[str] = {row[0] for row in rows.fetchall()}

    total_fetched = total_inserted = total_skipped = 0
    to_insert: list[dict] = []

    for cfg in CONFIGS:
        name        = cfg["name"]
        ids         = cfg["ids"]
        model_line  = cfg["model_line"]
        cfg_variant = cfg["variant"]

        cfg_fetched = cfg_queued = cfg_skipped = 0
        page = 1

        print(f"[{name}]")
        while MAX_PAGES is None or page <= MAX_PAGES:
            try:
                items = fetch_page(ids, page)
            except Exception as exc:
                print(f"  page {page} ERROR: {exc}")
                break

            if not items:
                break

            cfg_fetched += len(items)

            for raw in items:
                rec = map_record(raw, model_line, cfg_variant)
                if rec is None:
                    cfg_skipped += 1
                    continue
                url = rec.get("auction_url")
                if url and url in existing_urls:
                    cfg_skipped += 1
                    continue
                if url:
                    existing_urls.add(url)
                to_insert.append(rec)
                cfg_queued += 1

            page += 1
            time.sleep(2)

        total_fetched  += cfg_fetched
        total_inserted += cfg_queued
        total_skipped  += cfg_skipped
        print(f"  fetched: {cfg_fetched} | queued: {cfg_queued} | skipped: {cfg_skipped}")
        time.sleep(5)

    if to_insert:
        async with AsyncSession() as session:
            session.add_all([AuctionResult(**r) for r in to_insert])
            await session.commit()

    db_path = os.path.join(BACKEND_DIR, "pcarmarket.db")
    print(
        f"\nTotal — fetched: {total_fetched} | inserted: {len(to_insert)} | "
        f"skipped: {total_skipped}"
    )
    print(f"Database: {db_path}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
