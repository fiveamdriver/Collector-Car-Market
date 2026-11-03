import json, re, sys, time, ssl, certifi, urllib.request
CTX = ssl.create_default_context(cafile=certifi.where())
S = sys.argv[1]
missing = {re.search(r"/vehicles/([^/]+)", r[1]).group(1): r for r in json.load(open(f"{S}/ba_missing.json"))}
crawls = [c["id"] for c in json.load(urllib.request.urlopen("https://index.commoncrawl.org/collinfo.json", timeout=60, context=CTX))]
crawls = [c for c in crawls if c >= "CC-MAIN-2021-43"]
hits, total = [], 0
for c in crawls:
    url = f"https://index.commoncrawl.org/{c}-index?url=broadarrowauctions.com/vehicles/*&output=json&filter=status:200"
    for attempt in range(3):
        try:
            body = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "CollectorCarMarket research (personal)"}), timeout=120, context=CTX).read().decode()
            break
        except Exception as e:
            body = ""; err = e; time.sleep(20)
    recs = []
    for l in body.splitlines():
        try:
            recs.append(json.loads(l))
        except ValueError:
            pass
    total += len(recs)
    for r in recs:
        m = re.search(r"/vehicles/([^/?]+)", r["url"])
        if m and m.group(1) in missing:
            hits.append({"lot": m.group(1), "crawl": c, **{k: r[k] for k in ("url", "timestamp", "filename", "offset", "length")}})
    print(c, len(recs), "pages;", len(hits), "hits so far", flush=True)
    time.sleep(3)
json.dump(hits, open(f"{S}/cc_hits.json", "w"), indent=1)
print("TOTAL pages", total, "| missing lots with a CC copy:", len({h['lot'] for h in hits}))
