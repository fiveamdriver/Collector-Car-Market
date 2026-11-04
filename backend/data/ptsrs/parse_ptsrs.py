#!/usr/bin/env python3
"""
Parse @ptsrs Instagram captions (exported from the in-browser collector) into
paint-to-sample evidence rows: one row per (post, PTS colour, car).

PTS status is generation-specific: Speed Yellow is a standard 996 colour and a
PTS colour on a 991.2 GT3 RS. Every row therefore carries its own model line,
generation and variant; nothing here says "colour X is PTS" on its own.

Input : ~/Projects/CollectorCarMarket-data/ptsrs/ptsrs_export*.json
        {shortcode: {"cap": first 400 chars, "date": ISO, "pass": key}}
Output: ptsrs_evidence.json next to the input (data stays out of the public repo)

Usage (from backend/):
    python data/ptsrs/parse_ptsrs.py [export.json]
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import date

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND)
from app.utils.cards_911 import VARIANT_MY  # noqa: E402

DATA_DIR = os.path.expanduser("~/Projects/CollectorCarMarket-data/ptsrs")

# "PTS Meissen Blue (meissenblau; non-metallic UNI; Z54) 992 Carrera GTS Coupe"
# "Paint to Sample Dark Sea Blue (meerblau; non-metallic UNI; A5G) Porsche 911 (992.1) Turbo 50 Years"
_PTS_HIT = re.compile(
    r"(?P<claim>\bPTS\b|Paint[- ]to[- ]Sample(?:\s+Plus)?|Sonderwunsch|special[- ]order)\s+"
    r"(?P<name>[A-Z0-9][\w’'/.-]*(?:\s+[A-Z0-9][\w’'/.-]*){0,4}?)\s*"
    r"\((?P<paren>[^)]{1,120})\)\s*(?P<model>[^.,;!?\n]{0,80})",
)
_CODE = re.compile(r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{3}\b")
_FORMERLY = re.compile(r"formerly\s+([^;)]+)", re.I)
_FINISH = re.compile(r"non[- ]metallic|\bUNI\b|metallic|pearl", re.I)
NOT_EVIDENCE = re.compile(r"test car|prototype|\bmule\b|\brender(?:ing)?s?\b|model car|scale model|1:18|1:43", re.I)
OTHER_BRAND = re.compile(r"\b(?:Audi|Lamborghini|Bentley|VW|Volkswagen|Ferrari|McLaren|BMW|Mercedes)\b")

# ── model text -> (model_line, generation, variant) ─────────────────────────
_SUBGEN = re.compile(r"\b(99[1-7])\.([12])\b")
_GEN = re.compile(r"\b(964|993|996|997|991|992|981|982|718|987|986|918|980)\b")
_VARIANTS_911 = [  # longest first
    ("GT3 RS 4.0", r"GT3 RS 4\.0"), ("GT2 RS", r"GT2 RS"), ("GT3 RS", r"GT3 RS"),
    ("GT3 Touring", r"GT3(?:\s+with)?\s+Touring"), ("GT3", r"GT3"), ("GT2", r"GT2"),
    ("Sport Classic", r"Sport Classic"), ("S/T", r"\bS/T\b"), ("Dakar", r"Dakar"),
    ("Speedster", r"Speedster"), ("Turbo S", r"Turbo S\b"), ("Turbo", r"Turbo"),
    ("R", r"\b911 R\b|\bR\b(?=\s|$)"), ("Carrera T", r"Carrera T\b"),
    ("Carrera GTS", r"(?:Carrera|Targa)\s*4?\s*GTS|\bGTS\b"), ("Targa", r"Targa"),
    ("Carrera 4S", r"Carrera 4S|\bC4S\b"), ("Carrera S", r"Carrera S\b|\bC2S\b"),
    ("Carrera 4", r"Carrera 4\b"), ("Carrera", r"Carrera"),
]


def model_of(text: str, posted: date) -> dict | None:
    t = text or ""
    if re.search(r"Cayman|Boxster|Spyder RS|GT4", t):
        line = "Boxster" if re.search(r"Boxster|Spyder", t) else "Cayman"
        var = next((v for v, p in (("GT4 RS", r"GT4 RS"), ("GT4", r"GT4"), ("Spyder RS", r"Spyder RS"),
                                   ("Spyder", r"Spyder"), ("GTS", r"GTS")) if re.search(p, t)), "base")
        gen = "718" if re.search(r"\b718\b|GT4 RS|Spyder RS|982", t) or posted.year >= 2017 else (
            "981" if re.search(r"\b981\b", t) else None)
        return {"model_line": line, "generation": gen, "variant": var, "gen_source": "text" if gen else None}
    if re.search(r"\b918\b", t):
        return {"model_line": "918 Spyder", "generation": "918 Spyder", "variant": "base", "gen_source": "text"}
    if re.search(r"Carrera GT\b", t):
        return {"model_line": "Carrera GT", "generation": "Carrera GT", "variant": "base", "gen_source": "text"}
    if re.search(r"Taycan|Cayenne|Macan|Panamera|\b356\b|\b964\b.*Singer", t):
        return {"model_line": "other", "generation": None, "variant": None, "gen_source": None}
    sub, fam = _SUBGEN.search(t), _GEN.search(t)
    # The car is the first generation named: "991 GT3 RS with 997.1 RS decals"
    # is a 991, not a 997.1. Same family ("997 GT3 RS (997.2)") keeps the phase.
    if sub and fam and fam.start() < sub.start() and fam.group(1) != sub.group(1):
        sub = None
        # The variant is the one named with that generation, not the later car.
        t = t[:_SUBGEN.search(t).start()]
    if not (sub or fam or re.search(r"\b911\b|GT3|GT2|Carrera|Turbo|Targa|Speedster|Sport Classic|Dakar|S/T", t)):
        return None
    variant = next((v for v, p in _VARIANTS_911 if re.search(p, t)), None)
    if variant == "GT3 Touring":
        variant = "GT3"
    if sub:
        return {"model_line": "911", "generation": f"{sub.group(1)}.{sub.group(2)}", "variant": variant,
                "gen_source": "text"}
    family = fam.group(1) if fam and fam.group(1) in ("964", "993", "996", "997", "991", "992") else None
    yr = re.search(r"(?:^|\s|‘|')((?:19|20)\d\d|’\d\d|'\d\d)\s+(?:Porsche\s+)?(?:911\s+)?(?:99\d|911|GT|Carrera|Turbo)", t)
    when, how = posted, "inferred from post date"
    if yr:
        y = yr.group(1).lstrip("’'")
        when, how = date(int(y) if len(y) == 4 else (1900 + int(y) if int(y) > 50 else 2000 + int(y)), 6, 1), "model year in text"
    return {"model_line": "911", "generation": infer_phase(family, variant, when, exact_year=bool(yr)), "variant": variant,
            "gen_source": how if family or variant else None, "family": family}


def infer_phase(family: str | None, variant: str | None, posted: date, exact_year: bool = False) -> str | None:
    """
    The car's .1/.2. Air-cooled families have no phases. A variant built in
    only one phase of its family (997 GT3 RS 4.0, 991 R) is that phase whatever
    the post date — historic cars get posted years later. Otherwise pick the
    phase whose model years contain the post year (new deliveries), and leave
    it unplaced if that's ambiguous — better unplaced than wrong.
    """
    if family in ("964", "993"):
        return family
    if variant:
        phases = [g for g, spans in VARIANT_MY.items() if (not family or g.startswith(family)) and variant in spans]
        if len(phases) == 1:
            return phases[0]
    if exact_year:  # a model year stated next to the car: no slack
        exact = [g for g, spans in VARIANT_MY.items() if (not family or g.startswith(family))
                 and (spans.get(variant or "Carrera") or (0, -1))[0] <= posted.year <= (spans.get(variant or "Carrera") or (0, -1))[1]]
        return exact[0] if len(exact) == 1 else None
    cands = []
    for gen, spans in VARIANT_MY.items():
        if family and not gen.startswith(family):
            continue
        span = spans.get(variant or "Carrera")
        if span and span[0] - 1 <= posted.year <= span[1] + 1:
            cands.append(gen)
    if len(cands) == 1:
        return cands[0]
    # Two candidates: prefer the one whose span contains the post year exactly.
    exact = [g for g in cands if VARIANT_MY[g][variant or "Carrera"][0] <= posted.year <= VARIANT_MY[g][variant or "Carrera"][1]]
    return exact[0] if len(exact) == 1 else None


# "Though not PTS/Custom Color, this Shark Blue ...", "non-PTS", "isn't PTS"
_NEGATED = re.compile(r"(?:\bnot|\bnon|n't|\bwithout|\bno)[\s-]*(?:a\s+|an\s+|actually\s+)?$", re.I)
_CLAIM = re.compile(r"\bPTS\b(?!RS)|Paint[- ]to[- ]Sample(?:\s+Plus)?|Sonderwunsch|special[- ]order", re.I)
_MODEL_TOKEN = (r"(?:Porsche\s+)?(?:911\s+)?(?:\(?99[1-7](?:\.[12])?\)?|718|Cayman|Boxster|GT[234]\b|Carrera\b|"
                r"Turbo\b|Targa\b|918\b|Sport Classic|Speedster|Dakar|S/T|911\b|RS\b)")
_TITLE = r"[A-Z0-9][\w’'/.-]*"
# Colour with a bracket that carries a paint code or a German name.
_COL_PAREN = re.compile(r"(?P<name>" + _TITLE + r"(?:\s+" + _TITLE + r"){0,6}?)\s*\((?P<paren>[^)]{1,120})\)")
# "PTS Brewster Green 911 R" — no bracket: Title-Case words right before a model.
# Also "PTS Lichtgrün (Light Green/Birch Green) 991 GT3 RS": a bracket of
# English names (no code, no German) between colour and model.
_COL_BARE = re.compile(r"(?:\bPTS\b|Paint[- ]to[- ]Sample)\s+(?P<name>(?:" + _TITLE + r"\s+){1,4}?)"
                       r"(?=(?:\([^)]{1,60}\)\s*)?" + _MODEL_TOKEN + r")")
# PTS “Gold Metallic” / Paint to Sample "Signal Green"
_COL_QUOTED = re.compile(r"(?:\bPTS\b|Paint[- ]to[- ]Sample)\s+[“\"](?P<name>[A-Z][^”\"]{2,40})[”\"]")
# "finished in PTS Ivory", "dressed in Paint to Sample Gulf Blue"
_COL_IN = re.compile(r"(?:finished|painted|dressed|presented|wearing)\s+in\s+(?:a\s+|the\s+)?(?:PTS|Paint[- ]to[- ]Sample)\s+"
                     r"(?P<name>" + _TITLE + r"(?:\s+" + _TITLE + r"){0,3})")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9@#“\"])")
_NOT_COLOUR = re.compile(r"^(?:the|a|an|this|first|known|brand|new|world|only|my|our|his|her|stunning|presenting|"
                         r"porsche|chassis|class|delivered|example|exclusive|rare|ptsrs)$", re.I)


_LEAD_JUNK = re.compile(r"^(?:\S+[’']s\s+|\d+\s+)?(?:(?:PTS|Paint|to|Sample|Plus|Exclusive|the|a|an)\s+)*", re.I)


def _clean_name(name: str) -> str | None:
    # "Another PTS Grey Black", "brand new Paint-to-Sample Light Ivory": the
    # colour is what follows the last claim inside the match.
    claims = list(re.finditer(r"\bPTS\b(?!RS)|Paint[- ]to[- ]Sample(?:\s+Plus)?", name, re.I))
    if claims:
        name = name[claims[-1].end():]
    words = name.strip().split()
    while True:  # "This PTS Olive Green": strip lead words until nothing changes
        before = list(words)
        words = _LEAD_JUNK.sub("", " ".join(words)).split()
        while words and _NOT_COLOUR.match(words[0].strip("’'“”\"")):
            words.pop(0)
        if words == before:
            break
    while words and (re.match(_MODEL_TOKEN, words[-1]) or re.fullmatch(r"98[1-7]|99[1-7]s?|911s?|Porsche", words[-1])):
        words.pop()
    if words and re.fullmatch(r"\d{4}|[@#].*|\S+\.com\S*", words[0]):
        return None
    name = " ".join(words).strip(" ,")
    return name if name and not re.fullmatch(r"[\d.()]+", name) else None


def _paren_info(paren: str) -> dict | None:
    """Bracket contents if they describe a paint: German name, finish, codes."""
    codes = _CODE.findall(paren)
    parts = [p.strip() for p in paren.split(";")]
    german = parts[0] if parts and re.fullmatch(r"[a-zäöüß0-9\- ]+", parts[0]) else None
    if not (codes or german):
        return None  # "(992.1)", "(chassis #12)": not a paint bracket
    fin = _FINISH.search(paren)
    return {"colour_de": german, "codes": codes, "formerly": _FORMERLY.findall(paren),
            "finish": ("solid" if re.search(r"non|UNI", fin.group(0), re.I) else "metallic") if fin else None}


_STD_LIST = re.compile(r"\b(standard|metallic|special)\s+colou?rs?\s*(?:\([^)]*\)\s*)?(?:are|include|:)\s*:?\s*(?P<list>[^.]{3,250})", re.I)
_STD_ONE = re.compile(r"\b(?:a|the)\s+standard\s+(?P<name>[A-Z][\w/-]*(?:\s+[A-Z][\w-]*){0,3})")


from app.utils.color_parser import _COLOR_WORD_RE, _COLORS_LOWER  # noqa: E402


def _is_colour_name(name: str) -> bool:
    """A real paint name: on the known Porsche list, or Title-Case words ending
    in a colour word ("Gentian Blue Metallic"). Not "Touring Package", "LED"."""
    n = (name or "").strip()
    return bool(n) and (n.lower() in _COLORS_LOWER or bool(_COLOR_WORD_RE.match(n))) and not re.search(
        r"Package|Glass|LED|wheels?|seats?|interior|leather|Ferrari", n, re.I)


def standard_statements(code, post, cap, posted) -> list:
    """Captions that state a car's factory palette ("The standard colors are:
    White, Black, Guards Red...") or call a colour standard ("a standard
    Chalk/Crayon"). Factory-colour evidence for THAT car only."""
    out = []
    for sent in _SENT.split(cap):
        model = model_of(sent, posted) or model_of(cap, posted)
        found = []
        for m in _STD_LIST.finditer(sent):
            tier = m.group(1).lower()
            for part in re.split(r",\s*|\s+and\s+", re.sub(r"\([^)]*\)", "", m.group("list"))):
                name = _clean_name(part.strip(" .;"))
                if name and re.match(r"[A-Z]", name) and len(name.split()) <= 4:
                    found.append((name, "standard" if tier == "standard" else tier))
        for m in _STD_ONE.finditer(sent):
            for part in m.group("name").split("/"):
                found.append((part.strip(), "standard"))
        found = [(n, t) for n, t in found if _is_colour_name(n)]
        for name, tier in found:
            out.append({"post": code, "url": f"https://www.instagram.com/p/{code}/", "date": post["date"][:10],
                        "colour": name, "tier": tier, "sentence": sent[:300],
                        **(model or {"model_line": None, "generation": None, "variant": None, "gen_source": None})})
    return out


def parse(export: dict) -> tuple[list, Counter]:
    rows, stats = [], Counter()
    parse.standard = []
    for code, post in export.items():
        cap, posted = post.get("cap") or "", date.fromisoformat(post["date"][:10])
        parse.standard += standard_statements(code, post, cap, posted)
        if not _CLAIM.search(cap):
            stats["no PTS claim"] += 1
            continue
        if NOT_EVIDENCE.search(cap):
            stats["not evidence (test car / other brand / render)"] += 1
            continue
        found = 0
        seen = set()
        for sent in _SENT.split(cap):
            if not _CLAIM.search(sent):
                continue
            cands = []
            for m in _COL_PAREN.finditer(sent):
                info = _paren_info(m.group("paren"))
                name = _clean_name(m.group("name"))
                if info and name:
                    cands.append((m.start(), m.end(), name, info))
            for m in _COL_IN.finditer(sent):
                name = _clean_name(m.group("name"))
                if name and not any(name == c[2] for c in cands):
                    cands.append((m.start("name"), m.end("name"), name, {"colour_de": None, "codes": [], "formerly": [], "finish": None}))
            for m in _COL_QUOTED.finditer(sent):
                name = _clean_name(m.group("name"))
                if name and not any(name == c[2] for c in cands):
                    cands.append((m.start("name"), m.end("name"), name, {"colour_de": None, "codes": [], "formerly": [], "finish": None}))
            for m in _COL_BARE.finditer(sent):
                name = _clean_name(m.group("name"))
                if name and not any(name == c[2] for c in cands):
                    cands.append((m.start(), m.end(), name, {"colour_de": None, "codes": [], "formerly": [], "finish": None}))
            # Position each candidate where its cleaned name starts (a match can
            # begin at the word "PTS" itself).
            cands = [(max(sent.find(n, st), st), en, n, i) for st, en, n, i in cands]
            claims = [c.end() for c in _CLAIM.finditer(sent) if not _NEGATED.search(sent[max(0, c.start() - 18):c.start()])]
            starts = sorted(c[0] for c in cands)
            for start, end, name, info in cands:
                # This colour's own PTS claim: the nearest claim before it, with
                # no other colour in between. In "PTS Gulf Orange, Horizon Blue
                # Metallic, ..." only Gulf Orange is claimed PTS. Model-first
                # phrasing ("PTS 992 GT3, Ruby Star (...)") still works.
                prior = [c for c in claims if c <= start]
                if not prior or any(prior[-1] <= o < start for o in starts if o != start):
                    continue
                key = (name.lower(), tuple(info["codes"]))
                if key in seen:
                    continue
                seen.add(key)
                after = sent[end:end + 90]
                stop = re.search(r"\s\d+\)\s|\bPTS\b|Paint[- ]to[- ]Sample|[,;]", after)
                nxt = [o for o in starts if o > start]
                if stop:
                    after = after[:stop.start()]
                if nxt and nxt[0] - end < len(after):
                    after = after[:max(0, nxt[0] - end)]
                before = sent[max(0, start - 90):start]
                model, src = model_of(after, posted), "after colour"
                if not model:
                    model, src = model_of(before, posted), "before colour"
                if not model:
                    model, src = model_of(cap, posted), "caption"
                if (not model or model.get("model_line") is None) and OTHER_BRAND.search(sent):
                    continue
                yr = re.search(r"(?:^|\s)((?:19|20)\d\d)\s+(?:Porsche\s+)?(?:911|99\d|718|Cayman|Boxster|GT|Carrera|Turbo)", sent)
                rows.append({
                    "post": code, "url": f"https://www.instagram.com/p/{code}/", "date": post["date"][:10],
                    "car_year": int(yr.group(1)) if yr else None, "year_basis": "stated" if yr else "post date",
                    "claim": _CLAIM.search(sent).group(0), "colour": name, **info,
                    "sentence": sent[:300], "model_from": src,
                    **(model or {"model_line": None, "generation": None, "variant": None, "gen_source": None}),
                })
                found += 1
        if not found:
            found += _claim_after_or_list(code, post, cap, posted, rows)
        stats["posts with evidence" if found else "PTS claim but no colour parsed"] += 1
        stats["evidence rows"] += found
    return rows, stats


_IS_PTS_FOR = re.compile(r"\bis\s+(?:indeed\s+|in fact\s+|also\s+)?PTS\s+(?:on|for)\s+(?:this|the)\s+"
                         r"(?P<model>.{2,60}?)(?=\s+(?:from|in|at|with|delivered)\b|[,;!?]|\.\s|$)")
_CLAUSE_COLOUR = re.compile(r"(?:\bthat|:|^)\s+(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})(?=[,(\s])")
_NUMBERED = re.compile(r"(?:^|\s)\d+[.)]\s+(?P<name>[A-Z][\w’'-]*(?:\s+[A-Z][\w’'-]*){0,3})(?=\s+\d+[.)]|\s*$|\s+[#(@📸])")


def _claim_after_or_list(code, post, cap, posted, rows) -> int:
    """Rarer phrasings, only tried when nothing else matched in the post:
    "Chalk (kreide; ...) ... is indeed PTS for this 991.2 C4S", and a numbered
    colour list under a PTS heading ("Which PTS 992 GT3 Touring ...? 1. Oslo
    Blue 2. Albert Blue")."""
    n = 0
    def add(name, info, model, sent, src):
        rows.append({"post": code, "url": f"https://www.instagram.com/p/{code}/", "date": post["date"][:10],
                     "claim": "PTS", "colour": name, **info, "sentence": sent[:300], "model_from": src,
                     **(model or {"model_line": None, "generation": None, "variant": None, "gen_source": None})})
    empty = {"colour_de": None, "codes": [], "formerly": [], "finish": None}
    for m in _IS_PTS_FOR.finditer(cap):
        lead = re.split(r"(?<!\b[A-Z])[.!?]\s", cap[:m.start()])[-1]  # same sentence (not split at "U.K.")
        pm = list(re.finditer(r"\(([^)]{1,120})\)", lead))
        info = (_paren_info(pm[-1].group(1)) if pm else None) or empty
        cm = _CLAUSE_COLOUR.search(lead)
        name = _clean_name(cm.group("name")) if cm else None
        if info.get("colour_de"):          # "(kreide; non-metallic UNI)" names the paint
            name = name if name and re.search(r"[a-z]{3}", name) and "." not in name else info["colour_de"].title()
        if name and ("." in name or not re.search(r"[a-z]{3}", name)):
            name = None
        if name:
            add(name, info, model_of(m.group("model"), posted), m.group(0), "after claim"); n += 1
    head = re.search(r"\bPTS\b\s+(?P<model>" + _MODEL_TOKEN + r"[^?.!\n]{0,40})", cap)
    if not n and head:
        model = model_of(head.group("model"), posted)
        for m in _NUMBERED.finditer(cap):
            name = _clean_name(m.group("name"))
            if name and model:
                add(name, empty, model, head.group(0) + " … " + m.group(0).strip(), "list heading"); n += 1
    return n


_B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def media_id(code: str) -> int:
    """Instagram shortcode -> media ID (first 11 chars; IDs grow with time)."""
    n = 0
    for ch in code[:11]:
        n = n * 64 + _B64.index(ch)
    return n


def load_export(path: str) -> dict:
    """
    {code: {cap, date, pass}} from either export shape: flat (interim) or keyed
    by collector pass ({ptsrs_v1: {...}, ptsrs_first: {...}}). A post seen in
    several passes keeps its longest caption (later passes saved full text).

    Dates: the collector's saved `date` was sometimes a neighbouring post's
    (the modal's <time> lagged a click), so every date is re-derived from the
    media ID: ms = id >> 23 is a timestamp up to a constant offset, fitted as
    the median of (saved date - ms) over all posts.
    """
    raw = json.load(open(path))
    flat: dict = {}
    if raw and all(k.startswith("ptsrs_") and isinstance(v, dict) for k, v in raw.items()):
        for key, posts in raw.items():
            for code, post in posts.items():
                old = flat.get(code)
                if not old or len(post.get("cap") or "") > len(old.get("cap") or ""):
                    flat[code] = {**post, "pass": key}
    else:
        flat = raw
    from datetime import datetime, timezone
    from statistics import median
    diffs = []
    for code, post in flat.items():
        if post.get("date"):
            saved = datetime.fromisoformat(post["date"].replace("Z", "+00:00")).timestamp() * 1000
            diffs.append(saved - (media_id(code) >> 23))
    offset = median(diffs)
    for code, post in flat.items():
        ms = (media_id(code) >> 23) + offset
        post["saved_date"] = post.get("date")
        post["date"] = datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()
    return flat


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA_DIR, "ptsrs_export.json")
    rows, stats = parse(load_export(src))
    out = os.path.join(DATA_DIR, "ptsrs_evidence.json")
    json.dump(rows, open(out, "w"), indent=1, ensure_ascii=False)
    json.dump(parse.standard, open(os.path.join(DATA_DIR, "ptsrs_standard_statements.json"), "w"), indent=1, ensure_ascii=False)
    stats["standard-colour statements"] = len(parse.standard)
    for k, v in stats.most_common():
        print(f"{v:6d}  {k}")
    print(f"-> {out}")
