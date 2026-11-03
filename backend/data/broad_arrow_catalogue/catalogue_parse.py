"""Parse a Broad Arrow catalogue (page texts from pdftext) into per-lot details_text.

Layout: a lot's title page holds "LOT n", title, Chassis/Engine/Documents, estimate,
then highlight bullets (each preceded by a marker line: ─ or →). The essay starts on
the following page(s) and runs until the next lot's title page. Small-format
catalogues (no essays) put several lots on one page.
"""
import json, re, sys

FOOTER_RE = re.compile(r"^.*\|\s*LOT\s+\d+\s*\|\s*\d+\s*$")
HEADER_RE = re.compile(r"^(\d+\s*\|\s*\d{1,2}\s+\w+\s+\d{4}\s*\|.*"
                       r"|\d+\s*\|\s*BROAD ARROW AUCTIONS.*"
                       r"|THE [A-Z|'’ ]+ AUCTION( \d{4})?\s*\|\s*\d+"
                       r"|\d+\s*\|\s*THE [A-Z|'’ ]+ AUCTION.*)$")
LOT_RE = re.compile(r"(?:^|\s)LOT\s+(\d+)\s*\n\s*(?:[^\w\s]+\s*)?((?:18|19|20)\d\d\s+[^\n]+(?:\n(?!Chassis|CHASSIS)[^\n]{1,60}){0,3})(?=\n\s*(?:Chassis|CHASSIS))")
MARKERS = {"─", "→", "—", "•"}
STOP_END = re.compile(r"(\b(and|with|of|in|a|an|the|to|for|by|from|on|its|over|plus|as|at|only|optional|original|this|rare|desirable|factory|its|their|is|was|are)|[,\-–/(])$", re.I)
META_RE = re.compile(r"(?i)^(chassis no|engine no|transmission no|body no|gearbox no|documents|estimate|[$€£]\s?[\d.,]+|offered without reserve|chf|coachwork by)")

def clean_page(p):
    p = p.replace("A HAGERTY COMPANY LOT ", "A HAGERTY COMPANY\nLOT ")
    return "\n".join(l for l in p.splitlines() if not FOOTER_RE.match(l.strip()) and not HEADER_RE.match(l.strip()))

def split_bullets(lines, k):
    lines = [l.strip() for l in lines if l.strip()]
    if k <= 1 or len(lines) <= 1:
        return [" ".join(lines)] if lines else []
    width = max(len(l) for l in lines)
    cands = []
    for i in range(1, len(lines)):
        nxt, prev = lines[i], lines[i - 1]
        if not (nxt[:1].isupper() or nxt[:1].isdigit()):
            continue
        score = 2 * (1 - len(prev) / width)
        if STOP_END.search(prev): score -= 3
        if prev.endswith((".", ")", "”", '"')): score += 0.5
        cands.append((score, i))
    cands.sort(key=lambda x: -x[0])
    cuts = sorted(i for _, i in cands[:k - 1])
    out, start = [], 0
    for c in cuts + [len(lines)]:
        out.append(" ".join(lines[start:c])); start = c
    return [re.sub(r"(\w)- (\w)", r"\1-\2", b) for b in out]

def parse(pages):
    pages = [clean_page(p) for p in pages]
    # (page index, offset, match) for every lot header
    heads = [(pi, m) for pi, p in enumerate(pages) for m in LOT_RE.finditer(p)]
    lots = {}
    for j, (pi, m) in enumerate(heads):
        lotno = m.group(1)
        if lotno in lots:
            continue
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        nxt = heads[j + 1] if j + 1 < len(heads) else None
        same_page_end = nxt[1].start() if nxt and nxt[0] == pi else len(pages[pi])
        first = pages[pi][m.end():same_page_end]
        # essay: following pages up to the next header's page (only when the next lot starts on a later page)
        essay_pages = []
        if not nxt or nxt[0] > pi:
            stop = nxt[0] if nxt else len(pages)
            for q in range(pi + 1, stop):
                essay_pages.append(pages[q])
            if nxt:
                essay_pages.append(pages[nxt[0]][:nxt[1].start()])
        meta, groups, k, cur = [], [], 0, []
        for l in (x.strip() for x in first.splitlines()):
            if not l:
                continue
            if l in MARKERS:
                if cur: groups.append((k, cur)); cur, k = [], 0
                k += 1; continue
            if not groups and k == 0:
                meta.append(l); continue
            cur.append(l)
        if cur: groups.append((k, cur))
        bullets = [b for kk, g in groups for b in split_bullets(g, max(kk, 1))]
        essay = " ".join(" ".join(x.strip() for x in p.splitlines() if x.strip()) for p in essay_pages)
        essay = re.sub(r"\s+", " ", re.sub(r"(\w)- (\w)", r"\1\2", essay)).strip()
        def meta_val(prefix):
            for x in meta:
                if x.lower().startswith(prefix):
                    return re.sub(r"(?i)^" + prefix + r"\.?\s*", "", x).strip()
        chassis, engine, docs = meta_val("chassis no"), meta_val("engine no"), meta_val("documents")
        hl = list(bullets)
        if docs: hl.append(f"Documents: {docs}")
        if chassis: hl.append(f"Chassis No. {chassis}")
        if engine: hl.append(f"Engine No. {engine}")
        if chassis: hl.append(f"Chassis: {chassis}")
        lots[lotno] = {"lot": lotno, "title": title, "chassis": chassis, "meta": meta, "page": pi,
                       "n_bullets": len(bullets),
                       "details_text": "\n".join(hl) + ("\n--\n" + essay if essay else "")}
    return lots

if __name__ == "__main__":
    pages = json.load(open(sys.argv[1]))
    lots = parse(pages)
    json.dump(lots, open(sys.argv[2], "w"), indent=1)
    print(sys.argv[1].split("/")[-1], len(lots), "lots;", sum("porsche" in v["title"].lower() for v in lots.values()), "Porsche;",
          sum(1 for v in lots.values() if v["n_bullets"] == 0), "with no bullets")
