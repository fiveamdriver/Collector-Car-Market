#!/usr/bin/env python3
"""
Decide which PTS-tagged cars are PTS beyond doubt, and record why in
auction_results.pts_basis. The site shows the PTS badge only when pts_basis is
set; paint_to_sample alone is the listing's own claim (kept for review).

A tagged car is verified by any one of:
  owner     PTS_OVERRIDES in app/services/derived.py (reviewed by hand)
  ptsrs     @ptsrs documents this colour as PTS on this exact model line +
            generation + variant, on a car within one model year
            (~/Projects/CollectorCarMarket-data/ptsrs/pts_evidence_table.json)
  document  the listing quotes factory paperwork naming PTS: option sticker
            codes L998/L999 or 98/99, window-sticker 789 or a priced PTS line,
            CoA / Kardex / window sticker / build sheet in the same sentence

Everything else stays tagged-but-unverified (no badge) until reviewed.
Never infers across generations or variants.

Usage (from backend/):
    python data/verify_pts.py            # dry run -> reports/pts_verify_<date>.csv
    python data/verify_pts.py --apply    # also writes pts_basis
"""
import asyncio
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.services.derived import PTS_OVERRIDES  # noqa: E402
from app.utils.lot_details import _PTS_NAME_RE  # noqa: E402

DATA = os.path.expanduser("~/Projects/CollectorCarMarket-data")
TABLE = os.path.join(DATA, "ptsrs", "pts_evidence_table.json")
CARRERA_FAMILY = {"Carrera", "Carrera S", "Carrera 4", "Carrera 4S", "Carrera GTS", "Carrera T"}

_PTS = r"(?:paint[-\s]?to[-\s]?sample|\bPTS\b)"
_PAPER = r"(?:certificate of authenticity|\bCoA\b|kardex|window sticker|monroney|option sticker|build sheet|factory invoice)"
FACTORY_DOC = re.compile(
    r"\bL99[89]\b|"                                                    # option sticker paint codes
    r"(?:option|paint)\s*code[^.\n]{0,12}\b(?:98|99)\b[^.\n]{0,40}" + _PTS + "|"
    r"\b789\b[^.\n]{0,60}" + _PTS + "|" + _PTS + r"[^.\n]{0,60}\b789\b|"
    r"\$[\d,]{3,}\s+" + _PTS + "|" + _PTS + r"\s+(?:option|colou?r|selection)\s+(?:at|for|priced at)\s+\$[\d,]{3,}|"
    + _PAPER + r"[^.\n]{0,120}" + _PTS + "|" + _PTS + r"[^.\n]{0,120}" + _PAPER,
    re.I)
# A paperwork hit must say the paper states it ("the CoA shows/confirms ...",
# "according to the window sticker"), not just list it ("offered with a build
# sheet"). Option codes and priced sticker lines stand on their own.
_STANDALONE = re.compile(r"\bL99[89]\b|\b789\b|\$[\d,]{3,}|code[^.\n]{0,12}\b(?:98|99)\b", re.I)
_PAPER_SAYS = re.compile(r"\b(?:shows?|showing|confirms?|confirming|lists?|listing|according to|per (?:the|its)|"
                         r"reveals?|indicates?|notes?|documents?|decod\w*|records?|states?)\b", re.I)
# Text that undoes a document hit: the paperwork names a PTS colour the car no
# longer wears, or the sentence is hedged.
DOUBT = re.compile(r"\b(?:resprayed|repainted|refinished|respray|repaint)\b[^.\n]{0,80}\b(?:in|to)\b|"
                   r"\bbelieved\b|\breportedly\b|\bpossibly\b|\bit would seem\b", re.I)


def norm(s: str) -> str:
    s = (s or "").lower().replace("gray", "grey").replace("’", "'")
    s = re.sub(r"\b(metallic|pearl|paint|pts|paint-to-sample|non-metallic|uni)\b", " ", s)
    return re.sub(r"[^a-z0-9' ]+", " ", re.sub(r"\s+", " ", s)).strip()


def load_ptsrs() -> dict:
    if not os.path.exists(TABLE):
        print(f"! {TABLE} missing: @ptsrs tier skipped")
        return {}
    by_car = defaultdict(list)
    for e in json.load(open(TABLE)):
        by_car[(e["model_line"], e["generation"])].append(e)
    return by_car


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "porsche_colours"))
import pts_dry_run as factory  # noqa: E402

# One-word basic colours: too loose to match a PTS post on ("PTS Black" may be
# a special black; a listing's "Black" is usually the standard one).
BASIC = {"black", "white", "red", "blue", "green", "grey", "silver", "yellow", "orange", "brown",
         "purple", "gold", "beige", "tan", "metallic"}


def on_factory_palette(r) -> str | None:
    """The colour is on Porsche's own chart/brochure for this car and model
    year: then a PTS post about another car can't make this one certain."""
    scope, _ = factory.scope_of(r)
    pal = factory.palette(scope, r["year"]) if scope else None
    if pal and factory.on_list(factory.norm(r["exterior_color"] or ""), pal[0]):
        return pal[2]
    return None


def ptsrs_basis(r, by_car) -> str | None:
    colour = norm(r["exterior_color"])
    if not colour or colour in BASIC or on_factory_palette(r):
        return None
    codes = set(re.findall(r"(?:paint|colou?r)\s*code[:\s#]*\(?L?([0-9A-Z]{3})\b", r["details_text"] or "", re.I))
    var = r["variant"] or ""
    for e in by_car.get((r["model_line"], r["generation"]), []):
        same_car = (e["variant"] == var or (var == "Cabriolet" and e["variant"] in CARRERA_FAMILY)
                    or r["model_line"] in ("Carrera GT", "918 Spyder"))
        same_colour = bool(codes & set(e["codes"])) or any(
            norm(n) == colour for n in [e["colour"]] + e.get("also_called", []))
        near = r["year"] is None or any(abs(y - r["year"]) <= 1 for y in e.get("car_years", []))
        if same_car and same_colour and near:
            return f'ptsrs: {e["colour"]} on {e["generation"]} {e["variant"]}, {e["example_posts"][0]}'
    return None


def document_basis(r) -> str | None:
    t = _PTS_NAME_RE.sub("", f'{r["lot_title"] or ""}\n{r["details_text"] or ""}')
    for sent in re.split(r"(?<=[.!?])\s+|\n", t):
        m = FACTORY_DOC.search(sent)
        if m and not DOUBT.search(sent) and (_STANDALONE.search(m.group(0)) or _PAPER_SAYS.search(sent)):
            return "document: " + sent.strip()[:200]
    return None


async def main(apply: bool):
    by_car = load_ptsrs()
    async with AsyncSessionLocal() as s:
        if apply:
            await s.execute(text("ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS pts_basis TEXT"))
            await s.commit()
        has_col = (await s.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = 'auction_results' "
            "AND column_name = 'pts_basis'"))).first()
        rows = (await s.execute(text(
            "SELECT id, year, model_line, generation, variant, exterior_color, lot_title, details_text, "
            "auction_url, sold_price, paint_to_sample, " + ("pts_basis" if has_col else "NULL AS pts_basis") +
            " FROM auction_results WHERE paint_to_sample"
        ))).mappings().fetchall()
        out, stats, updates = [], Counter(), []
        for r in rows:
            ov = PTS_OVERRIDES.get(r["id"])
            basis = (f"owner: {ov[1]}" if ov and ov[0] else None) or ptsrs_basis(r, by_car) or document_basis(r)
            tier = basis.split(":")[0] if basis else "unverified"
            stats[tier] += 1
            out.append({"tier": tier, "id": r["id"], "year": r["year"],
                        "car": f'{r["model_line"]} {r["generation"]} {r["variant"]}',
                        "colour": r["exterior_color"], "basis": basis or "", "price": r["sold_price"],
                        "url": r["auction_url"], "title": (r["lot_title"] or "")[:90]})
            if basis != r["pts_basis"]:
                updates.append({"id": r["id"], "b": basis})
        if apply:
            # Clear stale bases on rows no longer tagged, then write.
            await s.execute(text("UPDATE auction_results SET pts_basis = NULL "
                                 "WHERE pts_basis IS NOT NULL AND paint_to_sample IS NOT TRUE"))
            if updates:
                await s.execute(text("UPDATE auction_results SET pts_basis = :b WHERE id = :id"), updates)
            await s.commit()
    order = {"unverified": 0, "document": 1, "ptsrs": 2, "owner": 3}
    out.sort(key=lambda o: (order[o["tier"]], o["car"], o["year"] or 0))
    os.makedirs(os.path.join(DATA, "reports"), exist_ok=True)
    path = os.path.join(DATA, "reports", f"pts_verify_{date.today()}.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{len(rows)} tagged PTS")
    for k, v in stats.most_common():
        print(f"{v:6d}  {k}")
    print(("applied " if apply else "dry run, would change ") + f"{len(updates)} rows -> {path}")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
