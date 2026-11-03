import json, re, sys
sys.path.insert(0, ".")
from app.utils.lot_details import extract
S = sys.argv[1]
CATS = {"zt26": ["zt26"], "po25": ["po25"], "po26": ["po26"], "ql26": ["ql26a", "ql26b"]}
def norm(s): return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.replace("“", '"').replace("”", '"').replace("’", "'")).strip().lower())
def close(a, b): return abs(a - b) <= max(60, 0.03 * max(a, b))
missing = [r for r in json.load(open(f"{S}/ba_missing.json")) if re.search(r"/vehicles/([a-z0-9]+)_", r[1]).group(1) in CATS]
lots = {}
for ev, cs in CATS.items():
    for c in cs:
        for k, v in json.load(open(f"{S}/catalogues/{c}_lots.json")).items():
            v = dict(v); v["ev"] = ev; v["key"] = f"{c}:{k}"; v["cm"] = extract(v["details_text"]).get("mileage"); lots[v["key"]] = v
# pass 1: exact titles; pass 2: prefix, only to lots nobody claimed exactly
claimed, assign, notes = set(), {}, {}
for pass_ in (1, 2):
    for _id, url, title, price, color, miles, year in missing:
        if url in assign: continue
        ev = re.search(r"/vehicles/([a-z0-9]+)_", url).group(1); t = norm(title)
        pool = [v for v in lots.values() if v["ev"] == ev and v["key"] not in claimed]
        c = [v for v in pool if norm(v["title"]) == t] if pass_ == 1 else \
            [v for v in pool if norm(v["title"]).startswith(t) or t.startswith(norm(v["title"]))]
        if len(c) > 1:
            m = None if miles in (None, "None") else int(miles)
            c2 = [v for v in c if m and v["cm"] and close(m, v["cm"])]
            if len(c2) == 1: c = c2
            else: notes[url] = f"ambiguous: {[v['key'] for v in c]}"; continue
        if len(c) == 1:
            assign[url] = c[0]; claimed.add(c[0]["key"])
accept, hold = {}, []
for _id, url, title, price, color, miles, year in missing:
    v = assign.get(url)
    if not v:
        hold.append((url, title, notes.get(url, "not in catalogue"))); continue
    m = None if miles in (None, "None") else int(miles)
    if m and v["cm"] and not close(m, v["cm"]):
        hold.append((url, title, f"MILEAGE CONFLICT db {m} vs catalogue {v['cm']} ({v['key']})")); continue
    accept[url] = v
json.dump({u: {"details_text": v["details_text"], "key": v["key"], "title": v["title"], "chassis": v["chassis"]} for u, v in accept.items()},
          open(f"{S}/catalogue_accept.json", "w"), indent=1)
json.dump(hold, open(f"{S}/catalogue_hold.json", "w"), indent=1)
print("accept", len(accept), "| hold", len(hold))
for h in hold: print("HOLD", h[0].split("/vehicles/")[1][:12], h[1][:48], "::", h[2])
print()
for u, v in accept.items():
    ex = extract(v["details_text"])
    col = ex.get("exterior_color")
    if col:
        src = next((b for b in v["details_text"].split("\n") if col.split()[0].lower() in b.lower()), "")[:150]
        print(f"{u.split('/vehicles/')[1][:12]:13}{col!s:26} <- {src}")
