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

  factory   the listing's colour is an exact Porsche colour name that is NOT on
            Porsche's complete factory range (standard + special) for this car
            and model year, nor the year either side, and the listing does not
            mention a repaint/wrap/modification (data/porsche_colours)

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


def _known_names() -> dict:
    """Every exact Porsche colour name we hold (any factory palette, any @ptsrs
    post), normalised the way the palette matcher normalises."""
    names = defaultdict(set)
    for p in list(factory.brochure.values()) + list(factory.chart.values()):
        for n, fin in p["names"].items():
            names[n] |= fin
    for es in load_ptsrs().values():
        for e in es:
            for n in [e["colour"]] + e.get("also_called", []):
                if n and _COLOUR_WORD.search(n):          # captions sometimes give model words
                    names[factory.norm(n)].add("any")
    return names


_KNOWN = None

# Paint no longer (or never) factory: respray, colour change, restomod family.
# Factory paint decides PTS (owner rule): touch-ups, panel refinishes, wheels/calipers repainted,
# or a respray in the ORIGINAL colour do not change it. Block only a colour change or a restomod.
_REPAINT = re.compile(r"\b(?:colou?r[- ]change\w*|custom paint\w*|backdate\w*|restomod|replica|outlaw|\bRWB\b|"
                      r"reimagined by singer|singer vehicle design|by singer\b|gunther werks|chameleon)\b", re.I)
_RECOLOURED = re.compile(r"\b(?:re-?paint(?:ed)?|re-?spray(?:ed)?|refinished|re-?finished)\s+(?:\w+\s+){0,3}?(?:in|to)\s+"
                         r"(?!(?:its|the|their|his|her)\s+(?:original|factory)|original|factory|the\s+same|matching)"
                         r"([A-Z][\w’'-]*(?:\s+[A-Z][\w’'-]*){0,3}|black|white|red|blue|green|grey|gray|silver|yellow|orange)", re.I)
# 'a tribute to the 1973 Carrera RS' is praise, not a replica: only the title or 'tribute car/build'
_TRIBUTE = re.compile(r"\btribute\s+(?:car|build|replica|conversion|recreation)\b", re.I)
# a real colour wrap, not 'features wrapped around a drivetrain' / 'leather-wrapped wheel'
_COLOUR_WRAP = re.compile(
    r"\b(?:vinyl|film|satin|matte?|gloss|colou?r|full[- ]body|full|partial|livery|paint[- ]protection|"
    r"black|white|grey|gray|silver|red|blue|green|yellow|orange|brown|gold|purple|pink)(?:[- ]\w+){0,2}[- ]wrap(?:ped|s)?\b|"
    r"\bwrapped\s+(?:in|with)\s+(?:a\s+)?(?:\w+\s+){0,2}(?:vinyl|film|satin|matte?|gloss|livery|"
    r"black|white|grey|gray|silver|red|blue|green|yellow|orange|brown|gold|purple|pink)\b|"
    r"\b(?:body|exterior|car)\s+(?:is\s+|was\s+)?wrapped\b", re.I)
_INTERIOR = re.compile(r"steering|wheel rim|leather[- ]wrapped|alcantara|race-tex|seat|dash|shift|gear ?(?:lever|knob)|interior|cabin|headliner", re.I)
_PPF = re.compile(r"protecti(?:on|ve)|\bPPF\b|xpel|clear[- ]?bra|stek|suntek", re.I)


def paint_changed(t: str, title: str = "", colour: str = "") -> bool:
    if _REPAINT.search(t) or _TRIBUTE.search(t) or re.search(r"\btribute\b", title or "", re.I):
        return True
    # 'repainted in Guards Red' when the car is listed as PTS Slate Grey -> colour changed
    for m in _RECOLOURED.finditer(t):
        if not _COLOUR_WORD.search(m.group(1)):          # 'refinished in February 2022'
            continue
        new = factory.norm(m.group(1))
        if colour and new and not (set(new.split()) & set(factory.norm(colour).split())):
            return True
    for sent in re.split(r"(?<=[.!?])\s+|\n", t):
        if _COLOUR_WRAP.search(sent) and not _PPF.search(sent) and not _INTERIOR.search(sent):
            return True
    return False


_PROCESS = re.compile(r"\b(?:two|single|one|three)[- ]?stage\b|\bclear[- ]?coat\b|\bbase[- ]?coat\b|\bpaint\b", re.I)
_MONTHS = "january february march april may june july august september october november december".split()
_BUILT = re.compile(r"(?:\bbuilt\s+(?:in|on)|production (?:completion )?date(?: of)?|manufactured\s+(?:in|on)|"
                    r"completed\s+(?:at\s+the\s+(?:zuffenhausen\s+)?(?:porsche\s+)?factory\s+)?on|left the factory (?:in|on))\b[^.\n]{0,25}?"
                    r"\b(" + "|".join(_MONTHS) + r")\b\.?\s+(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?((?:19|20)\d\d)", re.I)


def build_model_year(t: str) -> int | None:
    """Model year implied by a stated build/completion date (MY changes in August)."""
    m = _BUILT.search(t)
    if not m:
        return None
    month = _MONTHS.index(m.group(1).lower()) + 1
    return int(m.group(2)) + (1 if month >= 8 else 0)


def _pts_sentence_for(colour: str, t: str) -> str | None:
    """The listing sentence that claims PTS and names this colour."""
    key = [w for w in re.findall(r"[a-z]+", colour.lower()) if w not in ("metallic", "paint")]
    for sent in re.split(r"(?<=[.!?])\s+|\n", t):
        if re.search(r"paint[- ]?to[- ]?sample|\bPTS\b|special[- ]order|individualfarbe", sent, re.I) \
                and key and all(w in sent.lower() for w in key):
            return sent
    return None


def _finish_next_to(colour: str, sent: str | None) -> str | None:
    """'non-metallic Slate Gray' / 'Slate Gray metallic' -- only words touching the colour
    name count ('Pure White ... Gold Metallic detailing' says nothing about the white)."""
    if not sent:
        return None
    pat = r"[\s-]+".join(re.escape(w) for w in colour.split())
    m = re.search(r"(?i)\b(non[- ]?metallic|solid|metallic)[\s,\"”’']+(?:paint[- ]to[- ]sample[\s,\"”’']+)?" + pat, sent) \
        or re.search(r"(?i)" + pat + r"[\s,]+(non[- ]?metallic|solid|metallic)\b", sent)
    if not m:
        return None
    w = m.group(1).lower()
    return "met" if w == "metallic" else "uni"


def factory_basis(r) -> str | None:
    """Porsche's complete factory range for this car + model year decides:
    the colour (in the finish the listing states) is not on it -> PTS."""
    if r["year"] is None or not r["exterior_color"]:
        return None
    # paint-process words are not part of a colour ('Two-Stage Black' is Black)
    plain = _PROCESS.sub(" ", r["exterior_color"]).strip()
    colour = factory.norm(plain)
    if not colour or norm(plain) in BASIC or colour in factory.GENERIC:
        return None
    scope, _ = factory.scope_of(r)
    # (a colour off the 911 range for that year is off the narrower Turbo range too)
    pal = factory.palette(scope, r["year"]) if scope else None
    if not pal or not pal[4]:                      # only a COMPLETE range can prove off-list
        return None
    t = f'{r["lot_title"] or ""}\n{r["details_text"] or ""}'
    sent = _pts_sentence_for(r["exterior_color"], t)
    # finish as the listing states it for this colour ('non-metallic Slate Grey' is off a
    # range that only has Slate Grey Metallic); the colour name itself may carry it
    finish = factory.listing_finish(r["exterior_color"]) or _finish_next_to(r["exterior_color"], sent)
    if factory.on_list(colour, pal[0], finish):
        return None
    # stated build date -> that model year's range too
    my_b = build_model_year(t)
    if my_b and my_b != r["year"]:
        alt = factory.palette(scope, my_b)
        if alt and factory.on_list(colour, alt[0], finish):
            return None
    if paint_changed(t, r["lot_title"] or "", r["exterior_color"] or ""):
        return None
    global _KNOWN
    if _KNOWN is None:
        _KNOWN = _known_names()
    # a real colour: a known Porsche name, or the colour the listing's own PTS claim names
    if not (factory.on_list(colour, _KNOWN) or sent):
        return None
    fin = {"uni": " (non-metallic)", "met": " (metallic)"}.get(finish, "")
    return f'factory: {r["exterior_color"]}{fin} not on Porsche complete {scope} MY{r["year"]} range ({pal[2]})'



# The PTS colour the listing names in its own words ("Paint-to-Sample Pure Orange",
# "Acid Green paint to sample", "PTS Grey Black"). The structured colour field is
# sometimes only the colour family ("Orange") or a factory wrap ("Matte Black").
_STATED_AFTER = re.compile(        # same line only; BaT bullets put the interior on the next line
    r"(?i:paint[- ]?to[- ]?sample|\bPTS\b|individualfarbe)[\"”’' \t:]*(?i:colou?r[ \t]+(?:of[ \t]+)?)?(?i:in[ \t]+)?"
    r"((?i:non[- ]?metallic[ \t]+|metallic[ \t]+)?[A-Z][\w’'-]*(?:[ \t]+[A-Za-z][\w’'-]*){0,3})")
_STATED_BEFORE = re.compile(
    r"(?:^|[.;,\n(]|\bin|finished in|painted)[ \t]*([A-Z][\w’'-]*(?:[ \t]+[A-Z][\w’'-]*){0,3})[ \t]+(?:\([\w ]+\)[ \t]+)?(?i:paint[- ]?to[- ]?sample)",
    re.M)


from app.utils.color_parser import _PTSRS_COLOUR_WORD as _COLOUR_WORD  # noqa: E402


def _match_known(phrase: str) -> str | None:
    """Longest leading run of words that is an exact known Porsche colour name
    ('Metallic Oryx White with' -> 'Metallic Oryx White')."""
    global _KNOWN
    if _KNOWN is None:
        _KNOWN = _known_names()
    words = phrase.split()
    for k in range(len(words), 0, -1):
        sub = " ".join(words[:k])
        n = factory.norm(sub)
        if (n and n not in factory.GENERIC and norm(sub) not in BASIC and _COLOUR_WORD.search(sub)
                and factory.on_list(n, _KNOWN)):
            return sub
    return None


def _proper_colour(phrase: str) -> str | None:
    """A colour name we don't know yet, taken as the listing writes it: leading
    capitalised words containing a colour word ('Arancio Boreallis', 'Ferrari Yellow')."""
    words = []
    for w in phrase.split():
        if not w[:1].isupper():
            break
        words.append(w.strip(",;:"))
    while words and words[0].lower() in ("the", "a", "an", "porsche"):
        words = words[1:]
    cand = " ".join(words)
    whole = any(_COLOUR_WORD.fullmatch(w.lower().strip("'’-")) for w in words)
    return cand if len(words) >= 2 and whole else None


def stated_pts_colours(r) -> list[str]:
    from app.utils.color_parser import scan_for_color
    t = f'{r["lot_title"] or ""}\n{r["details_text"] or ""}'
    out = []
    for rx in (_STATED_AFTER, _STATED_BEFORE):
        for m in rx.finditer(t):
            c = _match_known(m.group(1)) or scan_for_color(m.group(1)) or _proper_colour(m.group(1))
            if c and not _COLOUR_WORD.search(c):
                c = None
            if c and norm(c) not in BASIC and factory.norm(c) not in factory.GENERIC and c not in out:
                out.append(c)
    return out


# Read one by one (2026-11-04): the listing names only a colour family, but Porsche's complete
# range for that exact car proves it (no colour of that family on the range).
# + the full read-through of every hidden claim (2026-11-04), one reason per car, in a data file
REVIEWED = {int(k): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                             "pts_reviewed_2026-11-04.json"))).items()}
REVIEWED.update({
    1667:  "997.2 GT3 RS 3.8 'Paint-To-Sample Black': range is Carrara White / Aqua Blue Met (+ Grey Black option) - no Black",
    17135: "997.2 GT3 RS 3.8 'one of three in Paint-to-Sample Black': no Black on the GT3 RS 3.8 range",
    18258: "997.2 GT3 RS 3.8 'one of nine paint-to-sample black cars': no Black on the GT3 RS 3.8 range",
    18023: "997.2 Speedster 'Paint-to-Sample Black', ordered via Porsche Exclusive: range is Pure Blue / Carrara White",
    9129:  "997.1 Turbo 'paint-to-sample Orange': no orange on the MY2007 997 Turbo range",
    17931: "993 Turbo MY1997 'paint-to-sample Pearl White Metallic': no pearl/metallic white on the 1997 993 range",
    12789: "1987 930 'special-order Orange Pearl Metallic': no orange on the 1987 911 range (standard + special)",
})


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
        has_col = (await s.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = 'auction_results' "
            "AND column_name = 'pts_basis'"))).first()
        if apply and not has_col:   # ALTER needs an exclusive lock; only when really missing
            await s.execute(text("ALTER TABLE auction_results ADD COLUMN IF NOT EXISTS pts_basis TEXT"))
            await s.commit()
            has_col = True
        rows = (await s.execute(text(
            "SELECT id, year, model_line, generation, variant, exterior_color, lot_title, details_text, "
            "auction_url, sold_price, paint_to_sample, " + ("pts_basis" if has_col else "NULL AS pts_basis") +
            " FROM auction_results WHERE paint_to_sample"
        ))).mappings().fetchall()
        out, stats, updates, colour_audit = [], Counter(), [], []
        for r in rows:
            ov = PTS_OVERRIDES.get(r["id"])
            basis = ((f"owner: {ov[1]}" if ov and ov[0] else None) or ptsrs_basis(r, by_car) or document_basis(r)
                     or factory_basis(r) or (f"review: {REVIEWED[r['id']]}" if r["id"] in REVIEWED else None))
            stated = stated_pts_colours(r)
            if not basis:
                # the listing's own PTS colour name, when the colour field is vaguer or a wrap
                for c in stated:
                    r2 = dict(r, exterior_color=c)
                    b = ptsrs_basis(r2, by_car) or factory_basis(r2)
                    if b:
                        basis = f"{b} [colour from listing text: {c}]"
                        break
            if stated and norm(stated[0]) != norm(r["exterior_color"] or ""):
                colour_audit.append({"id": r["id"], "stored": r["exterior_color"], "stated_pts": " | ".join(stated),
                                     "car": f'{r["year"]} {r["model_line"]} {r["generation"]} {r["variant"]}',
                                     "url": r["auction_url"]})
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
    order = {"unverified": 0, "review": 1, "factory": 2, "document": 3, "ptsrs": 4, "owner": 5}
    out.sort(key=lambda o: (order[o["tier"]], o["car"], o["year"] or 0))
    os.makedirs(os.path.join(DATA, "reports"), exist_ok=True)
    path = os.path.join(DATA, "reports", f"pts_verify_{date.today()}.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    apath = os.path.join(DATA, "reports", f"pts_colour_audit_{date.today()}.csv")
    with open(apath, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "car", "stored", "stated_pts", "url"])
        w.writeheader()
        w.writerows(colour_audit)
    print(f"{len(colour_audit)} cars where the listing names a different PTS colour than the colour field -> {apath}")
    print(f"{len(rows)} tagged PTS")
    for k, v in stats.most_common():
        print(f"{v:6d}  {k}")
    print(("applied " if apply else "dry run, would change ") + f"{len(updates)} rows -> {path}")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
