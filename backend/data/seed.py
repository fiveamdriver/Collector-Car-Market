#!/usr/bin/env python3
"""
Seed the database with 200 realistic Porsche auction results.
Run from the backend/ directory:
    python data/seed.py
"""
import asyncio
import os
import random
import sys
from datetime import date, timedelta

# Ensure backend/ is on sys.path regardless of where this script is invoked from
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import app.models  # noqa: F401 — registers ORM classes with Base.metadata
from app.database import Base
from app.models.listing import AuctionResult
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(BACKEND_DIR, 'pcarmarket.db')}"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

GENERATIONS = {
    "911":    ["964", "993", "996", "997.1", "997.2", "991.1", "991.2", "992"],
    "Cayman": ["987", "981", "718"],
    "Boxster": ["986", "987", "981", "718"],
}

ALL_VARIANTS = {
    "911":    ["Carrera", "Carrera S", "Carrera T", "Turbo", "Turbo S", "GT3", "GT3 RS", "GTS"],
    "Cayman": ["base", "S", "R", "GTS", "GT4", "GT4 RS"],
    "Boxster": ["base", "S", "GTS", "Spyder"],
}

# Variants restricted to specific generations
VARIANT_GEN_CONSTRAINTS = {
    "Carrera T": {"991.1", "991.2", "992"},
    "R":         {"987"},
    "GT4 RS":    {"718"},
    "Spyder":    {"981", "718"},
}

# Weight for picking each variant — rare trims appear less often
VARIANT_WEIGHTS = {
    "Carrera":   10, "Carrera S": 10, "Carrera T":  4,
    "Turbo":      5, "Turbo S":   3,
    "GT3":        4, "GT3 RS":    2,  "GTS":         7,
    "base":      10, "S":        10,  "R":           2,
    "GTS":        7, "GT4":       4,  "GT4 RS":      2,
    "Spyder":     4,
}

YEAR_RANGES = {
    "964": (1989, 1994), "993": (1994, 1998), "996": (1998, 2005),
    "997.1": (2005, 2008), "997.2": (2009, 2012),
    "991.1": (2012, 2016), "991.2": (2016, 2019), "992": (2019, 2024),
    "986": (1997, 2004), "987": (2005, 2012), "981": (2013, 2016), "718": (2017, 2024),
}

# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

PRICE_RANGES = {
    "GT3 RS":   (180_000, 355_000),
    "GT4 RS":   (168_000, 320_000),
    "GT3":      (105_000, 215_000),
    "GT4":       (88_000, 185_000),
    "Turbo S":  (148_000, 290_000),
    "Turbo":     (88_000, 175_000),
    "Spyder":    (72_000, 140_000),
    "R":         (62_000, 118_000),
    "GTS":       (60_000, 115_000),
    "Carrera T": (56_000,  96_000),
    "Carrera S": (46_000,  86_000),
    "S":         (46_000,  86_000),
    "Carrera":   (30_000,  66_000),
    "base":      (24_000,  52_000),
}

# Multipliers reflect collector demand by generation
GENERATION_MULTIPLIERS = {
    "964": 1.45, "993": 1.65, "996": 0.72,
    "997.1": 1.00, "997.2": 1.12,
    "991.1": 1.18, "991.2": 1.28, "992": 1.38,
    "986": 0.52, "987": 0.88, "981": 1.00, "718": 1.12,
}

# ---------------------------------------------------------------------------
# Transmission
# ---------------------------------------------------------------------------

# Base probability of manual per generation
MANUAL_PROBABILITY = {
    "964": 1.00, "993": 1.00, "996": 0.85, "986": 0.85,
    "997.1": 0.80, "987": 0.75,
    "997.2": 0.55, "981": 0.50,
    "991.1": 0.45, "991.2": 0.45, "992": 0.38, "718": 0.45,
}

GT_VARIANTS = {"GT3", "GT3 RS", "GT4", "GT4 RS", "R", "Spyder"}

# ---------------------------------------------------------------------------
# Mileage
# ---------------------------------------------------------------------------

MILEAGE_RANGES = {
    "964": (18_000, 115_000), "993": (15_000, 95_000), "996": (22_000, 125_000),
    "997.1": (12_000, 85_000), "997.2": (8_000, 75_000),
    "991.1": (5_000, 55_000), "991.2": (3_000, 45_000), "992": (500, 25_000),
    "986": (25_000, 130_000), "987": (18_000, 90_000),
    "981": (8_000, 60_000), "718": (2_000, 35_000),
}

# ---------------------------------------------------------------------------
# Misc lookup tables
# ---------------------------------------------------------------------------

COLORS = [
    "Guards Red", "Black", "Carrara White Metallic", "GT Silver Metallic",
    "GT Yellow", "Miami Blue", "Shark Blue", "Arctic Silver Metallic",
    "Meteor Grey Metallic", "Lava Orange", "Speed Yellow", "Jet Black Metallic",
    "Rhodium Silver Metallic", "Python Green", "Gulf Blue", "Gentian Blue Metallic",
    "Chalk", "Crayon", "Agate Grey Metallic", "Mahogany Metallic",
    "Birch Green Metallic", "Iris Blue Metallic",
]

AUCTION_SOURCES = ["BaT", "Cars & Bids", "RM Sothebys", "Mecum"]
AUCTION_SOURCE_WEIGHTS = [50, 25, 15, 10]

MODEL_LINE_WEIGHTS = {"911": 50, "Cayman": 30, "Boxster": 20}

# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------

def valid_variants(model_line: str, generation: str) -> tuple[list[str], list[int]]:
    names, weights = [], []
    for v in ALL_VARIANTS[model_line]:
        constraint = VARIANT_GEN_CONSTRAINTS.get(v)
        if constraint is None or generation in constraint:
            names.append(v)
            weights.append(VARIANT_WEIGHTS.get(v, 5))
    return names, weights


def pick_transmission(variant: str, generation: str) -> str:
    p = 0.80 if variant in GT_VARIANTS else MANUAL_PROBABILITY.get(generation, 0.50)
    return "manual" if random.random() < p else "pdk"


def pick_price(variant: str, generation: str) -> int:
    lo, hi = PRICE_RANGES[variant]
    mult = GENERATION_MULTIPLIERS.get(generation, 1.0)
    raw = random.randint(int(lo * mult), int(hi * mult))
    return round(raw / 500) * 500  # round to nearest $500


def make_lot_title(year: int, model_line: str, generation: str,
                   variant: str, color: str, transmission: str) -> str:
    t = "Manual" if transmission == "manual" else "PDK"
    options = [
        f"{year} Porsche {model_line} {variant}",
        f"{year} Porsche {model_line} {generation} {variant}",
        f"{year} Porsche {model_line} {variant} – {color}",
        f"{year} Porsche {model_line} {variant} ({t})",
        f"{year} Porsche {model_line} {generation} {variant} – {color}, {t}",
    ]
    return random.choice(options)


def random_sold_date() -> date:
    today = date.today()
    return today - timedelta(days=random.randint(0, 3 * 365))


def generate_record() -> dict:
    model_line = random.choices(
        list(MODEL_LINE_WEIGHTS), weights=list(MODEL_LINE_WEIGHTS.values())
    )[0]
    generation = random.choice(GENERATIONS[model_line])
    variant_names, variant_weights = valid_variants(model_line, generation)
    variant = random.choices(variant_names, weights=variant_weights)[0]

    year_lo, year_hi = YEAR_RANGES[generation]
    year = random.randint(year_lo, year_hi)
    transmission = pick_transmission(variant, generation)
    mileage = random.randint(*MILEAGE_RANGES[generation])
    color = random.choice(COLORS)
    sold_price = pick_price(variant, generation)
    auction_source = random.choices(AUCTION_SOURCES, weights=AUCTION_SOURCE_WEIGHTS)[0]
    sold_date = random_sold_date()
    lot_title = make_lot_title(year, model_line, generation, variant, color, transmission)

    return dict(
        make="Porsche",
        model_line=model_line,
        generation=generation,
        variant=variant,
        year=year,
        transmission=transmission,
        mileage=mileage,
        color=color,
        sold_price=sold_price,
        auction_source=auction_source,
        sold_date=sold_date,
        lot_title=lot_title,
        auction_url=None,
        paint_to_sample=None,
        production_number=None,
    )

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def seed(n: int = 200):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    records = [generate_record() for _ in range(n)]

    async with AsyncSessionLocal() as session:
        session.add_all([AuctionResult(**r) for r in records])
        await session.commit()

    print(f"Inserted {n} auction results into {os.path.join(BACKEND_DIR, 'pcarmarket.db')}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
