#!/usr/bin/env python3
"""
DRY RUN — never writes. Compares each car's listed exterior colour with Porsche's
own factory colour lists (this folder) and reports what needs a human look.

Rules (agreed 2026-11-03):
 1. Models without a palette are reported as "no palette", never as suspect:
    GT2/GT3/RS/specials, 991 (except the MY2012 launch brochure), 992, 997 MY2006
    and MY2011+, 996 MY2005, and anything else not covered.
 2. Evidence is ranked: a factory chart (complete list) beats a brochure
    (standard range only — absence there is weaker). A palette with colours we
    couldn't translate is "partial" and capped at low.
 3. A PTS tag backed by documentation (option code 98/99, window-sticker code
    789, Certificate of Authenticity / build sheet naming PTS) is never flagged.
 4. Paint code first (when the listing quotes one), then name.
 5. A colour that's absent this model year but listed the year before or after
    is "edge of availability" — a soft flag, not a contradiction.
 6. Resprays happen: "not on the list" is a reason to review, never proof of PTS.

Usage (from backend/):  python data/porsche_colours/pts_dry_run.py [out.csv]
"""
import asyncio
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from brochure_transcription import AUDIT, BROCHURES  # noqa: E402
from brochure_transcription_2 import BROCHURES_2  # noqa: E402
from colour_names import DE_EN, NOT_A_COLOUR  # noqa: E402

# ── Palettes ────────────────────────────────────────────────────────────────
_NORM_DROP = re.compile(r"\b(metallic|met|pearl|perlcolor|paint|non-metallic|uni|solid|porsche)\b\.?", re.I)


_ALIASES = [  # listing spellings -> Porsche's
    (r"\baventurine\b", "aventura"), (r"\bguard red\b", "guards red"), (r"\bindian red\b", "guards red"),
    (r"\bindischrot\b", "guards red"), (r"\bblack pearl\b", "black"), (r"\bschwarz\b", "black"),
    (r"\bcarrera white\b", "carrara white"), (r"\bgaurds?\b", "guards"),   # common listing misspellings
]
# Title words the colour parser sometimes keeps ("Original-Owner Silver Metallic").
_NOT_COLOUR_WORDS = re.compile(r"\b(original|owner|one|mile|miles|kilometer|kilometers|\d+k?)\b", re.I)
COLOUR_WORDS = {"black", "white", "red", "blue", "green", "grey", "silver", "yellow", "orange", "brown",
                "gold", "beige", "violet", "purple", "dark", "light"}


def norm(name: str) -> str:
    n = (name or "").lower().replace("gray", "grey").replace("-", " ")
    n = _NOT_COLOUR_WORDS.sub(" ", n)
    n = re.sub(r"\(.*?\)", " ", n)
    n = _NORM_DROP.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip(" .,")
    for pat, rep in _ALIASES:
        n = re.sub(pat, rep, n)
    return n


def distinctive(n: str) -> frozenset:
    return frozenset(t for t in n.split() if t not in COLOUR_WORDS)


def de_base(de: str) -> str:
    """'oceanblau-met.' -> 'oceanblau' (listings sometimes give the German name)."""
    return norm(re.sub(r"[- ]?(met\.?|metallic|perlcolor)$", "", de.strip()))


def _hues(n: str) -> frozenset:
    return frozenset(t for t in n.split() if t in COLOUR_WORDS and t != "metallic")


def on_list(colour: str, names: dict, finish: str | None = None) -> bool:
    """Colour (and finish, when the listing states one) is on the palette.
    Same distinctive words AND the same hue words: 'Jet Green' is not 'Jet Black',
    'Carrara White' is 'Carrara White' ('Ruby Star' vs 'Ruby Star Neo' stay distinct)."""
    d = distinctive(colour)
    h = _hues(colour)
    for n, finishes in names.items():
        if n == colour or (d and d == distinctive(n) and (not h or not _hues(n) or h == _hues(n))):
            if finish is None or finish in finishes:
                return True
    return False


_FINISH_UNI = re.compile(r"non[- ]?metallic|\bsolid\b|\buni\b", re.I)
_FINISH_MET = re.compile(r"(?<!non-)(?<!non )\bmetallic\b|\bpearl", re.I)
# The colour named in a paint-to-sample statement ("finished in paint-to-sample
# non-metallic Slate Gray over ...") — the colour field is sometimes the interior.
_PTS_COLOUR = re.compile(
    r"paint[- ]to[- ]sample[\"”’' ]*\s+((?:non[- ]?metallic |metallic |solid )?"
    r"[A-Z][\w’'-]*(?: [A-Z][\w’'-]*){0,3})", re.I)


def listing_finish(text: str) -> str | None:
    if _FINISH_UNI.search(text or ""):
        return "uni"
    if _FINISH_MET.search(text or ""):
        return "met"
    return None


GENERIC = {norm(x) for x in (
    "Silver", "Red", "Blue", "White", "Green", "Grey", "Yellow", "Orange", "Brown", "Purple",
    "Gold", "Beige", "Bronze", "Tan", "Maroon", "Burgundy", "Teal", "Charcoal", "Light Blue",
    "Dark Grey", "Dark Green", "Light Grey", "Two-Tone", "Custom", "Other", "Matte Black")}

CHART_SCOPE = {  # overview chart -> (model_line, generations or None, variants excluded)
    "911 (ab 1972)": "911air", "964 Carrera (ab 1989)": "911air", "993 Carrera (ab 1993)": "911air",
    "996 Carerra (ab 1998)": "996", "996 Turbo": "996turbo", "986 Boxster (ab 1997)": "986",
}
chart = defaultdict(lambda: {"names": defaultdict(set), "codes": set(), "partial": False})
for row in json.load(open(os.path.join(HERE, "factory_palettes_overview.json"))):
    de = re.sub(r"\s+", " ", row["name_de"]).strip()
    if de in NOT_A_COLOUR:
        continue
    p = chart[(CHART_SCOPE[row["chart"]], row["model_year"])]
    p["codes"].add(row["code"])
    finish = "uni" if "U" in row["paint"] else "met"
    p["names"][de_base(de)].add(finish)
    if de in DE_EN:
        p["names"][norm(DE_EN[de][0])].add(finish)
    else:
        p["partial"] = True

brochure = defaultdict(lambda: {"names": defaultdict(set), "codes": set(), "src": set(), "complete": False})
_BROCHURE_SCOPE = {  # file -> scope keys it adds to (scope, MY)
    "964-1991": [("911air", 1991)], "964-1992": [("911air", 1992)], "964-1993": [("911air", 1993)],
    "964-1995": [("911air", 1995)], "993-1996": [("911air", 1996)], "993-1997": [("911air", 1997), ("986", 1997)],
    "993-1998": [("911air", 1998), ("996", 1998), ("986", 1998)], "996-1999": [("996", 1999), ("986", 1999)],
    "997-2005": [("997", 2005)], "997-2006": [("997turbo", 2007)], "997-2007": [("997", 2007)],
    "997-2008": [("997", 2008)], "997-2009": [("997", 2009)], "997-2010": [("997", 2010)],
    "997-2012": [("991launch", 2012)], "carrera-gt-2003": [("cgt", None)], "918-spyder": [("918", None)],
}
for b in BROCHURES + BROCHURES_2:
    if "scopes" in b:
        scopes = b["scopes"]
    else:
        key = next((k for k in _BROCHURE_SCOPE if b["file"].startswith(k)), None)
        if not key:
            continue
        scopes = _BROCHURE_SCOPE[key]
    complete = b["complete"] if "complete" in b else AUDIT.get(b["file"], {}).get("complete", False)
    for scope in scopes:
        p = brochure[scope]
        p["src"].add(f'{b["file"]} p{b["page"]}')
        p["complete"] = p["complete"] or complete
        for tier, entries in b["tiers"].items():
            for code, name, _ in entries:
                finish = "met" if tier == "metallic" or "metallic" in name.lower() else "uni"
                p["names"][norm(name)].add(finish)
                if code:
                    p["codes"].add(code)

AIR_EXCLUDED = re.compile(r"RS|GT2|Turbo S|Slant Nose|Club Sport|Speedster|America", re.I)
WATER_EXCLUDED = re.compile(r"GT2|GT3|RS|R$|Speedster|Sport Classic|S/T|Dakar|Turbo S|GTS", re.I)
NINE97_RANGE = {"Carrera", "Carrera S", "Carrera 4", "Carrera 4S", "Targa", "Cabriolet"}


def scope_of(r) -> tuple[str | None, str]:
    ml, gen, var, my = r["model_line"], r["generation"], r["variant"] or "", r["year"]
    if ml == "Carrera GT":
        return "cgt", ""
    if ml == "918 Spyder":
        return "918", ""
    if ml == "Boxster" and gen == "986":
        return "986", ""
    # model-specific ranges (GT, 718/981): key "<model_line>|<generation>|<variant>"
    key = f"{ml}|{gen}|{var}"
    if any(k[0] == key for b in BROCHURES_2 for k in b.get("scopes", [])):
        return key, ""
    if ml in ("Boxster", "Cayman") and gen == "718" and var in ("base", "S", "GTS"):
        if var == "GTS" and not (my and my >= 2021):      # GTS 4.0 (MY21+) shares the base range
            return None, "718 GTS 2.5: no range yet"
        return "718|base", ""
    if ml in ("Boxster", "Cayman") and gen == "718" and var == "T":
        return "718|T", ""
    if ml in ("Boxster", "Cayman") and gen in ("987.1", "987.2"):
        if var not in ("base", "S"):
            return None, f"{ml} {var}: special/limited model, no palette"
        return ("987b" if ml == "Boxster" else "987c"), ""
    if ml != "911":
        return None, "model not covered by the colour PDFs"
    if gen in ("F-Body", "G-Body", "964", "993"):
        if AIR_EXCLUDED.search(var):
            return None, f"{var}: special/limited model, no palette"
        return "911air", ""
    if gen in ("996.1", "996.2"):
        if WATER_EXCLUDED.search(var):
            return None, f"{var}: GT/special model, no palette"
        return ("996turbo" if "Turbo" in var else "996"), ""
    if gen in ("997.1", "997.2"):
        if var == "Turbo":
            return "997turbo", ""
        if var not in NINE97_RANGE:
            return None, f"997 {var}: no palette"
        return "997", ""
    # Carrera family only (GTS / T / Turbo / GT models have their own ranges and brochures)
    if gen == "991.2" and var in ("Carrera", "Carrera S", "Carrera 4", "Carrera 4S", "Cabriolet", "Targa"):
        return "991.2", ""
    if gen == "992.1" and (var in ("Carrera", "Carrera S", "Carrera 4", "Carrera 4S", "Cabriolet")
                           or (var == "Targa" and my and my >= 2021)):
        return "992", ""
    if gen == "992.2" and var in ("Carrera", "Carrera S", "Carrera 4", "Carrera 4S", "Carrera GTS", "Cabriolet", "Targa"):
        return "992.2", ""
    if gen == "992.1" and var == "S/T":
        return "992st", ""
    if gen == "992.1" and var == "Dakar":
        return "992dakar", ""
    if gen == "991.1" and my == 2012 and var in ("Carrera", "Carrera S", "Cabriolet"):
        return "991launch", ""
    return None, f"{gen}: no palette yet"


def palette(scope, my):
    """(names, codes, evidence, partial) for scope + model year, or None."""
    my_key = None if scope in ("cgt", "918", "992st", "992dakar") else my
    c, b = chart.get((scope, my_key)), brochure.get((scope, my_key))
    if not c and not b:
        return None
    names = defaultdict(set)
    for src in (c, b):
        for n, fin in (src["names"].items() if src else ()):
            names[n] |= fin
    codes = (c["codes"] if c else set()) | (b["codes"] if b else set())
    evidence = "factory chart" if c else "brochure"
    partial = bool(c and c["partial"])
    # complete: Porsche's whole range (standard + special) for this scope+MY is on file, so an
    # off-list colour can be called PTS. A brochure flagged complete, or an overview chart
    # whose every German name maps to English (not partial).
    complete = bool((b and b["complete"]) or (c and not c["partial"]))
    return names, codes, evidence, partial, complete


# ── Listing evidence ─────────────────────────────────────────────────────────
PTS_DOC = re.compile(
    r"(?:option|paint)\s*code[^.\n]{0,12}\b(?:98|99)\b|\b(?:98|99)\b[^.\n]{0,12}paint[- ]to[- ]sample|"
    r"\b789\b[^.\n]{0,60}paint[- ]to[- ]sample|paint[- ]to[- ]sample[^.\n]{0,60}\b789\b|"
    r"(?:certificate of authenticity|\bCoA\b|build sheet|window sticker|monroney|kardex)"
    r"[^.\n]{0,120}(?:paint[- ]to[- ]sample|\bPTS\b)|"
    r"(?:paint[- ]to[- ]sample|\bPTS\b)[^.\n]{0,120}(?:certificate of authenticity|\bCoA\b|build sheet|window sticker|monroney|kardex)",
    re.I)
MODIFIED = re.compile(
    r"repaint|re-paint|respray|refinish|\bwrap(?:ped)?\b|modified|backdate|\bRWB\b|safari|outlaw|restomod|"
    r"tribute|replica|conversion|chameleon|custom|by singer|gunther|\bmatte?\b|ferrari", re.I)
CODE_IN_TEXT = re.compile(r"(?:paint|colou?r)\s*code[:\s#]*\(?L?([0-9A-Z]{2,4})\b", re.I)


async def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pts_dry_run.csv")
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            "SELECT id, model_line, generation, variant, year, exterior_color, paint_to_sample, "
            "lot_title, details_text, auction_source, sold_price FROM auction_results "
            "WHERE model_line IN ('911', 'Carrera GT', '918 Spyder', 'Boxster')"))).mappings().fetchall()
    stats, flags = Counter(), []
    for r in rows:
        pts = bool(r["paint_to_sample"])
        scope, why = scope_of(r)
        pal = palette(scope, r["year"]) if scope else None
        if not pal:
            stats[("PTS-tagged" if pts else "untagged", "no palette")] += 1
            continue
        names, codes, evidence, partial, _complete = pal
        txt = f'{r["lot_title"] or ""}\n{r["details_text"] or ""}'
        if pts and PTS_DOC.search(txt):
            stats[("PTS-tagged", "documented — kept")] += 1
            continue
        side = "PTS-tagged" if pts else "untagged"
        if MODIFIED.search(f'{r["lot_title"] or ""} {r["exterior_color"] or ""}'):
            stats[(side, "modified / repainted / wrapped — not assessed")] += 1
            continue
        hit = CODE_IN_TEXT.search(r["details_text"] or "")
        code = hit.group(1).upper() if hit else None
        raw_colour = r["exterior_color"] or ""
        if pts:
            m = _PTS_COLOUR.search(txt)
            if m and not re.match(r"(?:colou?r|paint|program|option|exterior|finish)", m.group(1), re.I):
                raw_colour = m.group(1)
        finish = listing_finish(raw_colour)
        colour = norm(raw_colour)
        if code and code in codes:
            listed, how = True, f"code {code}"
        elif not colour or colour in GENERIC:
            stats[(side, "colour too generic / missing")] += 1
            continue
        else:
            listed, how = on_list(colour, names, finish), "name" + (f" ({finish})" if finish else "")
        near = (not listed) and any(
            on_list(colour, (palette(scope, r["year"] + d) or [{}])[0], finish) for d in (-1, 1))
        if pts and listed:
            level = "low" if partial else ("high" if evidence == "factory chart" else "medium")
            kind = f"Likely wrong PTS tag: Porsche's {evidence} lists this as a factory colour for this model year"
        elif pts:
            stats[(side, "consistent (colour not on factory list)")] += 1
            continue
        elif listed:
            stats[(side, "factory colour — fine")] += 1
            continue
        elif near:
            level, kind = "soft", "colour listed the year before/after — edge of availability"
        else:
            level = "low" if (partial or evidence == "brochure") else "medium"
            kind = f"colour not on Porsche's {evidence} for this model year — review (PTS candidate or later respray)"
        stats[("PTS-tagged" if pts else "untagged", f"REVIEW [{level}]")] += 1
        flags.append({"level": level, "finding": kind, "matched_by": how, "id": r["id"], "year": r["year"],
                      "car": f'{r["generation"]} {r["variant"]}', "listed_colour": raw_colour,
                      "pts_tag": pts, "source": r["auction_source"], "price": r["sold_price"],
                      "title": (r["lot_title"] or "")[:90]})
    order = {"high": 0, "medium": 1, "soft": 2, "low": 3}
    flags.sort(key=lambda f: (order[f["level"]], not f["pts_tag"], -(f["price"] or 0)))
    with open(out_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(flags[0]) if flags else ["id"])
        w.writeheader()
        w.writerows(flags)
    for k, v in sorted(stats.items()):
        print(f"{v:6d}  {k[0]:<11} {k[1]}")
    print(f"\n{len(flags)} cars to review -> {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
