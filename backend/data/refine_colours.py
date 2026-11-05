#!/usr/bin/env python3
"""Exact exterior colour names from the lot text we already hold (2026-11-04).

Many rows store only a colour family ('Black' from Mecum's EXTERIOR COLOR field)
or nothing, while the same listing names the exact paint ('Basalt Black Metallic
paint ...', 'finished in Arena Red Metallic over ...').

Rules (accuracy first; unknown beats wrong):
  * exterior context only: 'finished/painted/presented/delivered/refinished in X',
    'X paint', 'X exterior', 'X over <interior>'; never a sentence about the
    interior, trim, wheels, calipers, stripes, livery, wrap/film
  * the name must be a known colour name (app/utils/color_parser vocabulary)
  * stored family -> refined only if the exact name contains the family word
    (Black -> Basalt Black Metallic, never -> Guards Red)
  * several different exact names -> left alone, listed for review

    python data/refine_colours.py           # dry run -> reports/colour_refine_<date>.csv
    python data/refine_colours.py --apply
"""
import asyncio
import csv
import os
import re
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.utils.color_parser import COLORS  # noqa: E402

DATA = os.path.expanduser("~/Projects/CollectorCarMarket-data")
FAMILY = {"cream", "pink", "violet", "lilac", "turquoise", "black", "white", "red", "blue", "green", "grey", "gray", "silver", "yellow", "orange", "brown",
          "purple", "gold", "beige", "tan", "bronze", "metallic", "silver metallic", "grey metallic",
          "gray metallic", "blue metallic", "red metallic", "green metallic", "black metallic", "white metallic",
          "brown metallic", "gold metallic", "light blue", "dark blue", "dark green", "dark grey", "dark gray",
          "light grey", "light gray", "metallic gray", "metallic grey", "metallic blue", "metallic silver",
          "metallic black", "metallic red", "metallic green", "maroon", "burgundy", "ivory", "cream", "teal"}
NOT_EXTERIOR = re.compile(
    r"interior|leather|upholster|seat|stitch|piping|carpet|alcantara|cloth|vinyl|velour|tartan|pasha|"
    r"headliner|dash|caliper|wheel|rim|centre cap|center cap|top\b|roof|hood lining|stripe|decal|graphic|"
    r"livery|wrap|film|belt|trim|steering|gauge|instrument|accent|badge|script|mirror", re.I)
STRONG = [
    re.compile(r"\b(?i:finished|painted|presented|refinished|resprayed|repainted|delivered|ordered|specified|"
               r"wearing|wears|dressed|clad|done)\s+(?i:new\s+)?(?i:in\s+|with\s+)?(?i:its\s+|a\s+|an\s+)?"
               r"(?i:factory[- ]original\s+|factory[- ]|original\s+|stunning\s+|rare\s+|classic\s+|striking\s+|period[- ]correct\s+)?"
               r"([A-Z][^.;\n]{2,60}?)(?=\s+over\b|\s+with\b|\s+and\b|\s+paint\b|[.,;:)\n]|$)"),
    re.compile(r"(?:^|[•*-]\s*)([A-Z][\w’'ü -]{2,50}?)(?:\s+\([A-Z0-9]{2,4}\))?\s+(?i:paint(?:work)?|exterior(?: colou?r| finish)?|finish)\b"),
    re.compile(r"(?:^|[•*-]\s*)([A-Z][\w’' -]{2,50}?)\s+(?:with|and)\s+[\w’'/ -]{0,40}(?:leather|interior|cloth|vinyl|alcantara|upholstery)\b", re.I),
    re.compile(r"(?:^|[•*-]\s*)([A-Z][\w’' -]{2,50}?)\s+over\s+[\w’' -]{0,40}(?:leather|interior|cloth|vinyl|alcantara|upholstery)", re.I),
]
# More exterior wordings (2026-11-04 audit of family-only rows):
#   a bullet line that is only the colour ('Guards Red', 'Polar Silver Metallic', 'Arctic Silver')
#   an adjective before it ('Rare Cobalt Blue', 'Factory Signal Red car', 'Original rare Smyrna Green car')
#   a code after it ('Grand Prix White/P5 Exterior')
_ADJ = r"(?:(?i:rare|very rare|original|factory|factory[- ]original|desirable|striking|stunning|attractive|porsche|period|uncommon|classic|beautiful|correct|matching)[ -]+){0,3}"
STRONG += [
    re.compile(r"^\s*[•*-]?\s*" + _ADJ + r"([A-Z][\w’'ü-]*(?: [A-Z][\w’'ü-]*){0,3})(?:\s*[/(]\s*[A-Z0-9]{2,4}\)?)?"
               r"(?:\s+(?i:paint|car|exterior|finish|example|over)\b.*)?\s*$"),
    re.compile(r"\b([A-Z][\w’'-]*(?: [A-Z][\w’'-]*){0,3})\s*/\s*[A-Z0-9]{2,4}\s+(?i:exterior|paint)\b"),
]
SPELLING_IN = {r"\bartic silver": "arctic silver", r"\bgrand prix\b(?! white)": "grand prix white"}

_PROPER = {}
for _c in COLORS:
    _PROPER.setdefault(re.sub(r"\s+", " ", _c.lower().replace("gray", "grey").replace("-", " ")), _c)
# one alternation, longest names first, whole words only
_NAMES_RX = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(_PROPER, key=len, reverse=True)) + r")\b")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().replace("gray", "grey").replace("-", " ")).strip()


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "porsche_colours"))
from colour_names import DE_EN  # noqa: E402  Porsche's German chart names -> English

_DE = {}
for _de, (_en, _src) in DE_EN.items():
    _DE[re.sub(r"[-. ]", "", _de.lower()).replace("met", "metallic").replace("metallicallic", "metallic")] = _en
    _DE[re.sub(r"[-. ]|met\.?$", "", _de.lower())] = _en.replace(" Metallic", "") if not _de.endswith("met.") else _en


# German names printed on Porsche's own cards next to the English (transcriptions)
try:
    from brochure_transcription import BROCHURES as _B1  # noqa: E402
    from brochure_transcription_2 import BROCHURES_2 as _B2  # noqa: E402
    for _b in _B1 + _B2:
        for _entries in _b["tiers"].values():
            for _code, _en, _note in _entries:
                for _q in re.findall(r"'([^']+)'", _note or ""):
                    _k = re.sub(r"[-. ]", "", _q.lower()).replace("ue", "ü")
                    if "metallic" in _en.lower() and "metallic" not in _k:
                        _DE.setdefault(_k + "metallic", _en)
                    _DE.setdefault(_k, _en)
except ImportError:
    pass


def _german(segment: str) -> str | None:
    k = re.sub(r"[-. ]", "", segment.lower())
    return _DE.get(k) or _DE.get(k.replace("metallic", ""))


_MODEL_NAMES = set("""carrera targa turbo speedster cabriolet coupe spyder boxster cayman panamera macan cayenne
sport classic club touring weissach heritage design edition gts gt2 gt3 gt4 rs porsche 911 912 914 918 924 928 944
959 968 356 exclusive""".split())


def _short_form(segment: str) -> str | None:
    """'Rubystone' -> 'Rubystone Red': a Porsche name the listing shortens by
    dropping the trailing colour-family word. Only if exactly one name fits."""
    words = [w for w in norm(segment).split() if w != "metallic"]
    # 'Red' must never grow into 'Red Orange'; a model name ('Carrera') must never grow into a paint
    if not 1 <= len(words) <= 3 or words[0] in FAMILY or any(w in _MODEL_NAMES for w in words):
        return None
    hits = set()
    for k, v in _PROPER.items():
        kw = k.split()
        rest = kw[len(words):]
        if kw[:len(words)] == words and 1 <= len(rest) <= 2 and all(w in FAMILY or w == "metallic" for w in rest):
            hits.add(v)
    # Solid and metallic are different paints: never add 'Metallic' the listing didn't
    # say, unless the name only exists as a metallic.
    said_met = "metallic" in norm(segment)
    plain = {h for h in hits if "metallic" not in norm(h)}
    met = hits - plain
    pick = (met if said_met else plain) or (met if not plain else set())
    return pick.pop() if len(pick) == 1 else None


import difflib  # noqa: E402


def _misspelt(segment: str) -> str | None:
    """'Azurro California' -> 'Azzurro California' (one-letter slips only)."""
    n = norm(segment)
    if len(n) < 8:
        return None
    m = difflib.get_close_matches(n, list(_PROPER), n=3, cutoff=0.92)
    m = [x for x in m if ("metallic" in x) == ("metallic" in n)]   # don't change the finish
    squash = {re.sub(r"(.)\1", r"\1", x) for x in m}                # 'azzurro' vs 'azzuro'
    return _PROPER[m[0]] if m and len(squash) == 1 else None


def _all_family(name: str) -> bool:
    """'Red Orange', 'Yellow-Green', 'Cream White': descriptions, not paint names."""
    return all(w in FAMILY or w == "metallic" for w in norm(name).split())


_OFFICIAL = None


def _official() -> set[str]:
    """Porsche's own names: factory cards, chart DE->EN map, @ptsrs evidence."""
    global _OFFICIAL
    if _OFFICIAL is None:
        import json
        names = {norm(en) for en, _ in DE_EN.values()}
        for _b in _B1 + _B2:
            for _entries in _b["tiers"].values():
                names |= {norm(n) for _, n, _ in _entries}
        tab = os.path.join(DATA, "ptsrs", "pts_evidence_table.json")
        if os.path.exists(tab):
            for e in json.load(open(tab)):
                names |= {norm(n) for n in [e["colour"]] + e.get("also_called", []) if n}
        _OFFICIAL = names
    return _OFFICIAL


def _acceptable(name: str, segment: str) -> bool:
    if not _all_family(name):
        return True
    # 'Cream White' (997 special) yes; 'red-orange' / 'yellow-green' descriptions no
    if norm(name) not in _official():
        return False
    words = norm(name).split()
    return bool(re.search(r"\b" + r"[\s-]+".join(w.capitalize() for w in words) + r"\b",
                          segment.replace("Gray", "Grey")))


_MODEL_WORD = re.compile(r"\b(?:gt[234]|rs|turbo|speedster|targa|cabriolet|coupe|spyder|boxster|cayman)\b", re.I)
# capitalised words that may sit next to a colour name without making it part of a longer name
_NEIGHBOUR_OK = set("""rare very original factory special order desirable striking stunning attractive porsche period
uncommon classic beautiful correct matching paint metallic exterior finish finished car example over with and in on of
the a an one owner new its this 911 912 930 964 993 996 997 991 992 914 924 928 944 968 356 959 carrera turbo targa
speedster coupe cabriolet rs gt2 gt3 gt4 sc s 4s spyder boxster cayman 918 sport classic edition rare-color""".split())


def _truncated(name: str, segment: str) -> bool:
    """'Bamboo' in 'Urban Bamboo ChromaFlair', 'Onyx' in 'Onyx Black interior'."""
    words = norm(name).split()
    pat = r"[\s-]+".join(re.escape(w) for w in words)
    for m in re.finditer(r"(?i)(?:([\w’'-]+)\s+)?" + pat.replace("grey", "gr[ae]y") + r"(?:\s+([\w’'-]+))?", segment):
        for nb in (m.group(1), m.group(2)):
            if nb and nb[0].isupper() and nb.lower() not in _NEIGHBOUR_OK:
                return True
    return False


def names_in(segment: str) -> list[str]:
    for a, b in SPELLING_IN.items():
        segment = re.sub(a, b, segment, flags=re.I)
    found = [_PROPER[m.group(1)] for m in _NAMES_RX.finditer(norm(segment))
             if _acceptable(_PROPER[m.group(1)], segment)
             and not _MODEL_WORD.search(_PROPER[m.group(1)])
             and not _truncated(_PROPER[m.group(1)], segment)]
    if not found:
        alt = _german(segment) or _short_form(segment) or _misspelt(segment)
        if alt and not _MODEL_WORD.search(alt) and not _truncated(alt, segment):
            found = [alt]
    return found


# Common misspellings of Porsche names in listings -> Porsche's spelling
SPELLING = {"carrera white": "Carrara White", "carrera white metallic": "Carrara White Metallic"}

_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n")


def exterior_names(t: str) -> list[str]:
    found = []
    for line in _SPLIT.split(t):
        if not line or len(line) > 400:
            line = line[:400]
        for rx in STRONG:
            for m in rx.finditer(line):
                seg = m.group(1)
                before = line[:m.start()]
                if NOT_EXTERIOR.search(seg) or re.search(r"\b(?:interior|upholster|leather|cabin)\b", before, re.I):
                    continue
                for n in names_in(seg):
                    if norm(n) not in FAMILY and n not in found:
                        found.append(n)
    return found


_FAM_ONLY = re.compile(r"(?i:\b(?:finished|painted|presented|refinished|resprayed|repainted)\s+in\s+(?:its\s+original\s+|original\s+)?)"
                       r"(?i:(black|white|red|blue|green|grey|gray|silver|yellow|orange|brown|purple|gold|beige|bronze)"
                       r"(?:\s+metallic)?)\b(?=\s+over\b|\s+with\b|[.,;\n]|$)|"
                       r"(?:^|[•*-]\s*)((?i:black|white|red|blue|green|grey|gray|silver|yellow|orange|brown|purple|gold|beige|bronze)(?:\s+metallic)?)\s+(?i:paint)\b", re.M)


def family_only(t: str) -> str | None:
    found = set()
    for line in _SPLIT.split(t):
        for m in _FAM_ONLY.finditer(line[:400]):
            if re.search(r"\b(?:interior|upholster|leather|wheel|caliper|stripe|top|roof|bumper)", line[:m.start()], re.I):
                continue
            found.add((m.group(1) or m.group(2)).title().replace("Gray", "Grey"))
    return found.pop() if len(found) == 1 else None


def family_words(stored: str) -> set[str]:
    return {w for w in norm(stored).split() if w != "metallic"}


_CUT = re.compile(r"\s+(?:over|with|on|and|in)\s+[^.\n]{0,40}?\b(?:leather|interior|upholster|cloth|vinyl|"
                  r"alcantara|seats?|leatherette|velour|tartan)\b", re.I)


def family_scan(t: str, fam: set[str]) -> list[str]:
    """Stored colour is a family ('Red'): find exact names containing that family
    word on lines about the paint (anything after 'with/over ... leather' cut off)."""
    out = []
    for line in _SPLIT.split(t):
        line = line[:300]
        m = _CUT.search(line)
        seg = line[:m.start()] if m else line
        if NOT_EXTERIOR.search(seg):
            continue
        for n in names_in(seg):
            if fam <= set(norm(n).split()) and not _all_family(n) and n not in out:
                out.append(n)
    return out


def decide(stored: str | None, t: str) -> tuple[str, str | None, list[str]]:
    cands = exterior_names(t)
    if stored and norm(stored) in FAMILY:
        fam = family_words(stored)
        fits = [c for c in cands if fam <= set(norm(c).split())]
        if not fits:
            fits = family_scan(t, fam)
            cands = cands + [f for f in fits if f not in cands]
        uniq = {norm(c).replace(" metallic", "") for c in fits}
        if len(uniq) == 1:
            best = max(fits, key=len)                       # 'Basalt Black Metallic' over 'Basalt Black'
            return "refine", best, cands
        return ("ambiguous" if len(uniq) > 1 else "no exact name"), None, cands
    if not stored:
        uniq = {norm(c).replace(" metallic", "") for c in cands}
        if len(uniq) == 1:
            return "fill", max(cands, key=len), cands
        if len(uniq) > 1:
            return "ambiguous", None, cands
        fam = family_only(t)
        if fam:
            return "fill family", fam, [fam]
        return "no colour in text", None, cands
    return "already exact", None, cands


async def main(apply: bool):
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text(
            "SELECT id, auction_url, exterior_color, lot_title, details_text, sold_price FROM auction_results "
            "WHERE details_text IS NOT NULL"))).mappings().fetchall()
    stats, out, updates = Counter(), [], []
    for r in rows:
        stored = r["exterior_color"]
        if stored and norm(stored) not in FAMILY:
            stats["already exact"] += 1
            continue
        t = f'{r["lot_title"] or ""}\n{r["details_text"] or ""}'
        verdict, new, cands = decide(stored, t)
        host = (r["auction_url"] or "").split("/")[2] if r["auction_url"] else ""
        stats[(verdict, host)] += 1
        if verdict in ("refine", "fill", "fill family", "ambiguous"):
            out.append({"verdict": verdict, "id": r["id"], "stored": stored, "new": new or "",
                        "candidates": " | ".join(cands), "price": r["sold_price"], "url": r["auction_url"]})
        if new:
            new = SPELLING.get(new.lower(), new)
            if stored and norm(new) == norm(stored):       # no-op ('Dark Blue' -> 'Dark Blue')
                continue
            updates.append({"i": r["id"], "c": new})
    path = os.path.join(DATA, "reports", f"colour_refine_{date.today()}.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["verdict", "id", "stored", "new", "candidates", "price", "url"])
        w.writeheader()
        w.writerows(sorted(out, key=lambda o: (o["verdict"], -(o["price"] or 0))))
    for k, v in sorted(stats.items(), key=lambda kv: str(kv[0])):
        print(f"{v:6d}  {k}")
    print(f"{len(updates)} rows would get an exact colour -> {path}")
    if apply and updates:
        async with AsyncSessionLocal() as s:
            await s.execute(text("UPDATE auction_results SET exterior_color = :c WHERE id = :i"), updates)
            await s.commit()
        print("applied")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
