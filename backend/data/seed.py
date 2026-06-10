#!/usr/bin/env python3
"""
Seed the database with 350 realistic Porsche auction results.
Clears all existing records first.
Run from the backend/ directory:  python data/seed.py
"""
import asyncio
import os
import random
import sys
from collections import namedtuple
from datetime import date, timedelta

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401
from app.database import Base
from app.models.listing import AuctionResult
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(BACKEND_DIR, 'pcarmarket.db')}"
engine        = create_async_engine(DATABASE_URL)
AsyncSession  = async_sessionmaker(engine, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Variant definitions
# V(name, weight, price_lo, price_hi, trans_rule, cap=None)
#   cap   – max records allowed for this variant (limited-production models)
#   trans – rule key into TRANS_PROBS
# ---------------------------------------------------------------------------

V = namedtuple('V', ['name', 'weight', 'price_lo', 'price_hi', 'trans', 'cap', 'year_lo', 'year_hi'],
               defaults=[None, None, None])

# Probability of manual transmission per rule
TRANS_PROBS = {
    'manual':       1.00,   # always manual
    'pdk':          0.00,   # always PDK / Tiptronic
    'very_early':   0.90,   # 964/993 Carrera era
    'early':        0.72,   # 996/997.1 Carrera; 964/993 Turbo
    'mid':          0.50,   # 997.2 Carrera; 997.x Turbo
    'modern':       0.38,   # 991/992 Carrera
    'gt':           0.80,   # GT3 / GT3 RS (not strict manual-only)
    'turbo_modern': 0.28,   # 991/992 Turbo
}

def pick_trans(rule: str) -> str:
    p = TRANS_PROBS.get(rule, 0.50)
    return 'manual' if random.random() < p else 'pdk'


VARIANT_DATA: dict[str, dict[str, list]] = {
    '911': {
        'F-Series': [
            V('911',                        8,   60_000,   150_000, 'manual'),
            V('911S',                       5,   80_000,   200_000, 'manual'),
            V('911T',                       6,   60_000,   150_000, 'manual'),
            V('911E',                       4,   60_000,   150_000, 'manual'),
            V('911L',                       3,   60_000,   150_000, 'manual'),
            V('911R',                       1,  800_000, 3_500_000, 'manual', 2),
            V('Carrera RS 2.7',             2,  400_000, 1_200_000, 'manual', 4),
            V('Carrera RS 2.7 Lightweight', 1,  800_000, 2_500_000, 'manual', 2),
            V('S/T',                        1,  300_000,   800_000, 'manual', 2),
        ],
        'G-Series': [
            V('Carrera 2.7',          5,  50_000,  120_000, 'manual', None, 1974, 1977),
            V('911S',                 4,  40_000,   90_000, 'manual', None, 1974, 1977),
            V('Carrera RS 3.0',       2, 200_000,  500_000, 'manual',    3, 1975, 1977),
            V('SC',                   6,  35_000,   80_000, 'manual', None, 1978, 1983),
            V('Carrera 3.2',          7,  50_000,  120_000, 'manual', None, 1984, 1989),
            V('Turbo 3.0',            3, 120_000,  250_000, 'manual', None, 1975, 1977),
            V('Turbo 3.3',            5, 100_000,  280_000, 'manual', None, 1978, 1989),
            V('Turbo 3.3 Slant Nose', 2, 200_000,  500_000, 'manual',    3, 1987, 1989),
            V('Turbo S',              1, 250_000,  600_000, 'manual',    2, 1980, 1980),
            V('Speedster',            2, 150_000,  350_000, 'manual',    4, 1989, 1989),
        ],
        '964': [
            V('Carrera',             8,  45_000,  88_000, 'very_early'),
            V('Carrera RS',          2, 200_000, 500_000, 'manual'),
            V('Carrera RS America',  2, 120_000, 250_000, 'manual'),
            V('Turbo',               4,  80_000, 162_000, 'early'),
            V('Turbo S',             2, 150_000, 300_000, 'early'),
            V('Speedster',           2, 150_000, 350_000, 'manual'),
            V('GTS',                 3,  68_000, 138_000, 'very_early'),
        ],
        '993': [
            V('Carrera',             7,  52_000, 102_000, 'very_early'),
            V('Carrera S',           5,  62_000, 122_000, 'very_early'),
            V('Carrera RS',          2, 300_000, 700_000, 'manual'),
            V('Turbo',               4,  90_000, 182_000, 'early'),
            V('Turbo S',             2, 150_000, 350_000, 'early'),
            V('GT2',                 1, 400_000, 900_000, 'manual'),
            V('Speedster',           2, 200_000, 450_000, 'manual'),
            V('GTS',                 3,  80_000, 152_000, 'very_early'),
        ],
        '996.1': [
            V('Carrera',             8,  24_000,  52_000, 'early'),
            V('Turbo',               4,  58_000, 122_000, 'early'),
            V('GT3',                 3,  80_000, 180_000, 'manual'),
        ],
        '996.2': [
            V('Carrera',             6,  28_000,  58_000, 'early'),
            V('Carrera S',           5,  35_000,  68_000, 'early'),
            V('Turbo',               4,  55_000, 112_000, 'early'),
            V('Turbo S',             3,  80_000, 162_000, 'early'),
            V('GT3',                 3,  80_000, 180_000, 'manual'),
            V('GT3 RS',              2, 120_000, 300_000, 'manual'),
            V('GT2',                 2, 150_000, 350_000, 'manual'),
        ],
        '997.1': [
            V('Carrera',             7,  42_000,  78_000, 'early'),
            V('Carrera S',           7,  50_000,  92_000, 'early'),
            V('Turbo',               4,  72_000, 138_000, 'mid'),
            V('GT3',                 3,  90_000, 168_000, 'gt'),
            V('GT3 RS',              2, 120_000, 280_000, 'manual'),
            V('GT2',                 2, 150_000, 350_000, 'manual'),
            V('Sport Classic',       1, 400_000, 700_000, 'manual', 3),
        ],
        '997.2': [
            V('Carrera',             7,  50_000,  92_000, 'mid'),
            V('Carrera S',           7,  58_000, 108_000, 'mid'),
            V('Carrera GTS',         3,  68_000, 118_000, 'mid'),
            V('Turbo',               4,  82_000, 148_000, 'mid'),
            V('Turbo S',             3,  98_000, 178_000, 'mid'),
            V('GT3',                 3, 100_000, 192_000, 'gt'),
            V('GT3 RS',              2, 140_000, 290_000, 'manual'),
            V('GT3 RS 4.0',          1, 300_000, 600_000, 'manual', 5),
            V('GT2 RS',              2, 250_000, 500_000, 'manual'),
            V('Speedster',           1, 150_000, 280_000, 'pdk'),
        ],
        '991.1': [
            V('Carrera',             7,  58_000,  98_000, 'modern'),
            V('Carrera S',           7,  68_000, 112_000, 'modern'),
            V('Carrera T',           3,  62_000, 102_000, 'modern'),
            V('Carrera GTS',         3,  78_000, 130_000, 'modern'),
            V('Turbo',               3, 102_000, 172_000, 'turbo_modern'),
            V('Turbo S',             3, 122_000, 218_000, 'turbo_modern'),
            V('GT3',                 3, 122_000, 208_000, 'gt'),
            V('GT3 RS',              2, 180_000, 350_000, 'gt'),
            V('R',                   1, 350_000, 600_000, 'manual', 4),
        ],
        '991.2': [
            V('Carrera',             7,  68_000, 108_000, 'modern'),
            V('Carrera S',           7,  78_000, 125_000, 'modern'),
            V('Carrera T',           3,  72_000, 118_000, 'modern'),
            V('Carrera GTS',         3,  88_000, 142_000, 'modern'),
            V('Turbo',               3, 112_000, 188_000, 'turbo_modern'),
            V('Turbo S',             3, 132_000, 228_000, 'turbo_modern'),
            V('GT3',                 3, 132_000, 220_000, 'gt'),
            V('GT3 RS',              2, 200_000, 400_000, 'gt'),
            V('GT2 RS',              2, 250_000, 450_000, 'manual'),
            V('Speedster',           1, 250_000, 450_000, 'manual', 5),
        ],
        '992': [
            V('Carrera',             6,  92_000, 138_000, 'modern'),
            V('Carrera S',           6, 105_000, 158_000, 'modern'),
            V('Carrera T',           3,  98_000, 148_000, 'modern'),
            V('Carrera GTS',         3, 112_000, 172_000, 'modern'),
            V('Turbo',               3, 152_000, 245_000, 'turbo_modern'),
            V('Turbo S',             3, 178_000, 285_000, 'turbo_modern'),
            V('GT3',                 3, 162_000, 258_000, 'gt'),
            V('GT3 RS',              2, 235_000, 425_000, 'gt'),
            V('GT2 RS',              1, 300_000, 600_000, 'manual'),
            V('S/T',                 1, 346_000, 806_000, 'manual', 3),
            V('Sport Classic',       1, 250_000, 450_000, 'manual', 5),
            V('Dakar',               2, 200_000, 320_000, 'modern'),
        ],
    },
    'Cayman': {
        '987': [
            V('base',   6, 22_000, 42_000, 'mid'),
            V('S',      6, 28_000, 52_000, 'mid'),
            V('R',      2, 55_000, 95_000, 'manual'),
            V('GTS',    3, 40_000, 70_000, 'mid'),
        ],
        '981': [
            V('base',   5, 38_000, 62_000, 'modern'),
            V('S',      5, 46_000, 76_000, 'modern'),
            V('GTS',    3, 56_000, 92_000, 'modern'),
            V('GT4',    3, 78_000, 142_000, 'manual'),
        ],
        '718': [
            V('base',   5, 52_000, 80_000, 'modern'),
            V('S',      5, 60_000, 90_000, 'modern'),
            V('GTS',    3, 68_000, 102_000, 'modern'),
            V('GT4',    3, 90_000, 155_000, 'manual'),
            V('GT4 RS', 2, 150_000, 285_000, 'manual'),
        ],
    },
    'Boxster': {
        '986': [
            V('base',      6, 11_000, 26_000, 'early'),
            V('S',         5, 14_000, 34_000, 'early'),
        ],
        '987': [
            V('base',      6, 22_000, 40_000, 'mid'),
            V('S',         6, 28_000, 50_000, 'mid'),
            V('Spyder',    2, 55_000, 105_000, 'manual'),
            V('GTS',       3, 38_000, 68_000, 'mid'),
        ],
        '981': [
            V('base',      5, 35_000, 58_000, 'modern'),
            V('S',         5, 42_000, 72_000, 'modern'),
            V('GTS',       3, 52_000, 86_000, 'modern'),
            V('Spyder',    2, 65_000, 118_000, 'manual'),
        ],
        '718': [
            V('base',      5, 46_000, 74_000, 'modern'),
            V('S',         5, 54_000, 84_000, 'modern'),
            V('GTS',       3, 62_000, 98_000, 'modern'),
            V('Spyder',    2, 72_000, 128_000, 'manual'),
            V('RS Spyder', 1, 100_000, 182_000, 'manual'),
        ],
    },
}

# Generation selection weights (higher = more records)
GEN_WEIGHTS = {
    '911': {
        'F-Series': 5, 'G-Series': 8,
        '964': 9, '993': 10, '996.1': 6, '996.2': 8,
        '997.1': 12, '997.2': 13, '991.1': 13, '991.2': 14, '992': 15,
    },
    'Cayman':  {'987': 8,  '981': 10, '718': 12},
    'Boxster': {'986': 5,  '987': 7,  '981': 8,  '718': 10},
}

MODEL_WEIGHTS = {'911': 55, 'Cayman': 28, 'Boxster': 17}

YEAR_RANGES = {
    'F-Series': (1964, 1973), 'G-Series': (1974, 1989),
    '964':   (1989, 1994), '993':   (1994, 1998),
    '996.1': (1998, 2001), '996.2': (2002, 2005),
    '997.1': (2005, 2008), '997.2': (2009, 2012),
    '991.1': (2012, 2016), '991.2': (2016, 2019), '992': (2019, 2024),
    '986':   (1997, 2004), '987':   (2005, 2012),
    '981':   (2012, 2016), '718':   (2016, 2024),
}

MILEAGE_RANGES = {
    'F-Series': (20_000, 180_000), 'G-Series': (30_000, 160_000),
    '964':   (15_000, 120_000), '993':   (12_000, 100_000),
    '996.1': (25_000, 128_000), '996.2': (22_000, 118_000),
    '997.1': (10_000,  88_000), '997.2': ( 8_000,  78_000),
    '991.1': ( 4_000,  58_000), '991.2': ( 2_000,  46_000), '992': (400, 28_000),
    '986':   (25_000, 135_000), '987':   (18_000,  95_000),
    '981':   ( 8_000,  65_000), '718':   ( 2_000,  38_000),
}

COLORS = [
    'Guards Red', 'Black', 'Carrara White Metallic', 'GT Silver Metallic',
    'GT Yellow', 'Miami Blue', 'Shark Blue', 'Arctic Silver Metallic',
    'Meteor Grey Metallic', 'Lava Orange', 'Speed Yellow', 'Jet Black Metallic',
    'Rhodium Silver Metallic', 'Python Green', 'Gulf Blue', 'Gentian Blue Metallic',
    'Chalk', 'Crayon', 'Agate Grey Metallic', 'Mahogany Metallic',
    'Birch Green Metallic', 'Iris Blue Metallic', 'Slate Grey Metallic',
    'Forest Green Metallic', 'Ruby Star Metallic', 'GT3 RS Orange',
]

AUCTION_SOURCES        = ['BaT', 'Cars & Bids', 'RM Sothebys', 'Mecum']
AUCTION_SOURCE_WEIGHTS = [50, 25, 15, 10]


# ---------------------------------------------------------------------------
# Record generation
# ---------------------------------------------------------------------------

def available_variants(model_line: str, generation: str, counts: dict) -> list:
    variants = VARIANT_DATA[model_line][generation]
    return [
        v for v in variants
        if v.cap is None or counts.get((model_line, generation, v.name), 0) < v.cap
    ]


def make_lot_title(year, model_line, generation, variant, color, trans) -> str:
    t = 'Manual' if trans == 'manual' else 'PDK'
    return random.choice([
        f'{year} Porsche {model_line} {variant}',
        f'{year} Porsche {model_line} {generation} {variant}',
        f'{year} Porsche {model_line} {variant} – {color}',
        f'{year} Porsche {model_line} {variant} ({t})',
        f'{year} Porsche {model_line} {generation} {variant} – {color}, {t}',
    ])


def random_sold_date() -> date:
    return date.today() - timedelta(days=random.randint(0, 3 * 365))


def generate_record(counts: dict) -> dict | None:
    model_line = random.choices(
        list(MODEL_WEIGHTS), weights=list(MODEL_WEIGHTS.values())
    )[0]
    gen_pool   = GEN_WEIGHTS[model_line]
    generation = random.choices(
        list(gen_pool), weights=list(gen_pool.values())
    )[0]

    pool = available_variants(model_line, generation, counts)
    if not pool:
        return None

    vdef  = random.choices(pool, weights=[v.weight for v in pool])[0]
    key   = (model_line, generation, vdef.name)
    counts[key] = counts.get(key, 0) + 1

    gen_yr    = YEAR_RANGES[generation]
    yr_lo     = vdef.year_lo if vdef.year_lo is not None else gen_yr[0]
    yr_hi     = vdef.year_hi if vdef.year_hi is not None else gen_yr[1]
    year      = random.randint(yr_lo, yr_hi)
    trans     = pick_trans(vdef.trans)
    mileage   = random.randint(*MILEAGE_RANGES[generation])
    color     = random.choice(COLORS)
    sold_price = round(random.randint(vdef.price_lo, vdef.price_hi) / 500) * 500
    source    = random.choices(AUCTION_SOURCES, weights=AUCTION_SOURCE_WEIGHTS)[0]
    sold_date = random_sold_date()
    lot_title = make_lot_title(year, model_line, generation, vdef.name, color, trans)

    return dict(
        make='Porsche',
        model_line=model_line,
        generation=generation,
        variant=vdef.name,
        year=year,
        transmission=trans,
        mileage=mileage,
        color=color,
        sold_price=sold_price,
        auction_source=source,
        sold_date=sold_date,
        lot_title=lot_title,
        auction_url=None,
        paint_to_sample=None,
        production_number=None,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def seed(n: int = 350):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession() as session:
        await session.execute(delete(AuctionResult))
        await session.commit()
    print('Cleared existing auction_results.')

    counts:  dict = {}
    records: list = []
    attempts = 0
    while len(records) < n and attempts < n * 30:
        attempts += 1
        rec = generate_record(counts)
        if rec:
            records.append(rec)

    async with AsyncSession() as session:
        session.add_all([AuctionResult(**r) for r in records])
        await session.commit()

    db_path = os.path.join(BACKEND_DIR, 'pcarmarket.db')
    print(f'Inserted {len(records)} auction results → {db_path}')
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(seed())
