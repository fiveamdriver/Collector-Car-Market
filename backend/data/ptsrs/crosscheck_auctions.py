#!/usr/bin/env python3
"""
DRY RUN — never writes. Cross-checks auction rows against the PTSRS evidence
table (build_evidence_table.py), matching on model line + generation + variant
+ colour. Nothing is inferred across generations or variants, except a
Cabriolet row (the site cards every open car on one Cabriolet card per
generation) matching evidence for that generation's Carrera-family cars.

Findings
  corroborated   tagged PTS and PTSRS documents this colour as PTS on this car
  candidate      NOT tagged, but PTSRS documents it as PTS on this car -> review
  hint           colour is PTS on another variant of the same generation (weak)
  uncorroborated tagged PTS, no PTSRS post for this colour on this car (info only)

Usage (from backend/):  python data/ptsrs/crosscheck_auctions.py
"""
import asyncio
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from sqlalchemy import text  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402

DATA_DIR = os.path.expanduser("~/Projects/CollectorCarMarket-data/ptsrs")
CARRERA_FAMILY = {"Carrera", "Carrera S", "Carrera 4", "Carrera 4S", "Carrera GTS", "Carrera T"}
GENERIC = {"silver", "red", "blue", "white", "green", "grey", "yellow", "orange", "brown", "black",
           "purple", "gold", "beige", "tan", "metallic"}


def norm(s: str) -> str:
    s = (s or "").lower().replace("gray", "grey").replace("azzuro", "azzurro").replace("’", "'")
    s = re.sub(r"\b(metallic|pearl|paint|pts|paint-to-sample|non-metallic|uni)\b", " ", s)
    return re.sub(r"[^a-z0-9' ]+", " ", re.sub(r"\s+", " ", s)).strip()


async def main():
    table = json.load(open(os.path.join(DATA_DIR, "pts_evidence_table.json")))
    by_car = defaultdict(list)
    for e in table:
        by_car[(e["model_line"], e["generation"])].append(e)
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            "SELECT id, model_line, generation, variant, year, exterior_color, paint_to_sample, lot_title, "
            "details_text, auction_source, sold_price, auction_url FROM auction_results "
            "WHERE model_line IN ('911','Cayman','Boxster','Carrera GT','918 Spyder') "
            "AND exterior_color IS NOT NULL"))).mappings().fetchall()
    stats, out = Counter(), []
    for r in rows:
        colour = norm(r["exterior_color"])
        if not colour or colour in GENERIC:
            continue
        codes = set(re.findall(r"(?:paint|colou?r)\s*code[:\s#]*\(?L?([0-9A-Z]{3})\b", r["details_text"] or "", re.I))
        ev = by_car.get((r["model_line"], r["generation"]), [])
        def same_colour(e):
            if codes and codes & set(e["codes"]):
                return True
            names = [e["colour"]] + e.get("also_called", [])
            return any(norm(n) == colour for n in names)
        var = r["variant"] or ""
        exact = [e for e in ev if same_colour(e) and (e["variant"] == var or (
            var == "Cabriolet" and e["variant"] in CARRERA_FAMILY) or r["model_line"] in ("Carrera GT", "918 Spyder"))]
        near = [e for e in exact if r["year"] is None or any(abs(y - r["year"]) <= 1 for y in e.get("car_years", []))]
        far = [e for e in exact if e not in near]
        exact = near
        other = [e for e in ev if same_colour(e) and e not in exact and e not in far] + far
        pts = bool(r["paint_to_sample"])
        if pts and exact:
            kind = "corroborated"
        elif pts:
            kind = "uncorroborated"
        elif exact:
            kind = "candidate"
        elif other:
            kind = "hint"
        else:
            continue
        stats[kind] += 1
        e = (exact or other)
        out.append({"finding": kind, "id": r["id"], "year": r["year"],
                    "car": f'{r["model_line"]} {r["generation"]} {var}', "colour": r["exterior_color"],
                    "pts_tag": pts, "ptsrs_posts": sum(x["posts"] for x in e),
                    "ptsrs_variants": ", ".join(sorted({x["variant"] for x in e})),
                    "example_post": e[0]["example_posts"][0] if e else "", "source": r["auction_source"],
                    "price": r["sold_price"], "url": r["auction_url"], "title": (r["lot_title"] or "")[:90]})
    order = {"candidate": 0, "uncorroborated": 1, "hint": 2, "corroborated": 3}
    out.sort(key=lambda o: (order[o["finding"]], -(o["ptsrs_posts"] or 0)))
    path = os.path.join(DATA_DIR, "crosscheck_auctions.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    for k, v in stats.most_common():
        print(f"{v:6d}  {k}")
    print("->", path)


if __name__ == "__main__":
    asyncio.run(main())
