
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-003 — Wiktionary miner for concrete visual noun seeds.

Mines en.wiktionary categories:
  en:Kitchen utensils, en:Hand tools, en:Office supplies
Filters: nouns-only pages, IP blocklist, <=3 words, lowercase en-US,
dedup against existing seeds (Layer 2 exact-duplicate).

Usage: python wiktionary_miner.py [target_count]   (default 60)
Output: data/raw/wiktionary_batch.json  (NOT auto-ingested; review first)
"""
import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import pathlib
from datetime import datetime, timezone

DB = engine_paths.CANON_DB
OUT = engine_paths.DATA_DIR / "raw" / "wiktionary_batch.json"

CATEGORIES = [
    "Category:en:Kitchenware",
    "Category:en:Tools",
    "Category:en:Stationery",
]

IP_BLOCKLIST = {
    # brands / trademarks / franchises commonly present in category listings
    "apple", "iphone", "ipad", "macbook", "ipod", "airpods",
    "samsung", "galaxy", "sony", "playstation", "nintendo", "switch",
    "xbox", "microsoft", "google", "kindle", "amazon", "alexa",
    "lego", "barbie", "disney", "pokemon", "pokeball", "lightsaber",
    "star wars", "harry potter", "marvel", "batman", "superman",
    "transformers", "hello kitty", "peppa", "simpsons", "mickey",
    "coca cola", "coke", "pepsi", "starbucks", "mcdonald", "ikea",
    "leica", "nikon", "canon", "gopro", "dji", "bosch", "dremel",
    "velcro", "ziploc", "tupperware", "kleenex", "jacuzzi",
    "post-it", "postit", "sharpie", "bic", "biro", "hoover",
}

STOPWORDS = {
    "list of", "gallery", "template", "wikipedia", "appendix", "index",
    "the ", "and ", "with ", "for ", "miscellaneous", "various",
}


def fetch_category(cat: str) -> list[str]:
    """Fetch category members via MediaWiki API (continuation-aware)."""
    titles = []
    cont = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cat,
            "cmlimit": "500",
            "cmtype": "page",
            "format": "json",
        }
        if cont:
            params["cmcontinue"] = cont
        url = "https://en.wiktionary.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "object-asset-engine/0.1 (seed miner)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for m in data.get("query", {}).get("categorymembers", []):
            titles.append(m["title"])
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(0.3)
    return titles


def passes_filters(title: str) -> bool:
    t = title.strip()
    low = t.lower()
    if ":" in t or "," in t or "(" in t or ")" in t:
        return False
    if len(t.split()) > 3 or len(t.split()) == 0:
        return False
    if any(w in low for w in STOPWORDS):
        return False
    words = set(low.split())
    if words & IP_BLOCKLIST:
        return False
    return True


def existing_canonicals() -> set[str]:
    conn = sqlite3.connect(DB)
    try:
        return {r[0].lower() for r in conn.execute("SELECT canonical_name FROM seeds")}
    finally:
        conn.close()


def main() -> None:
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    seen = existing_canonicals()
    picked = []
    report = {}
    # pass 1: fetch all candidates per category (no cap), pass 2: round-robin fill
    pool: dict[str, list[dict]] = {}
    for cat in CATEGORIES:
        members = fetch_category(cat)
        ok = []
        for m in members:
            low = m.lower().strip()
            if low in seen:
                continue
            if passes_filters(m):
                ok.append(low)
                seen.add(low)
        label = cat.replace("Category:en:", "")
        pool[label] = [
            {
                "master_source_id": None,
                "canonical_name": w,
                "aliases": [],
                "object_class": "concrete_visual",
                "category_path": f"wiktionary.{label.lower().replace(' ', '_')}",
                "existence_type": "real",
                "demand_signal": None,
                "source_wiktionary_category": cat,
            }
            for w in ok
        ]
        report[label] = {"members_fetched": len(members), "passed_filters": len(ok)}
        print(f"{label}: fetched={len(members)} kept={len(ok)}")
    # round-robin fill until target
    while len(picked) < target and any(pool.values()):
        for label in list(pool):
            if pool[label] and len(picked) < target:
                picked.append(pool[label].pop(0))
    for i, p in enumerate(picked):
        p["master_source_id"] = f"WIKI-{i+1:03d}"
    OUT.write_text(json.dumps(picked, indent=2), encoding="utf-8")
    print(f"total_kept={len(picked)} target={target}")
    print(f"saved={OUT}")
    print(json.dumps(report))
    print(f"generated_at={datetime.now(timezone.utc).isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
