"""OPCODE-AUDIT-001 — Gemini stateless audit worker (pilot 1,000 kata).

Flow:
  1. audit_queue table (pilot: 500 not_in_wordnet + 300 h4_capital + 200 eligible-control)
  2. One API call per 1,000 words -> JSONL verdicts
  3. Verdicts -> audit_queue + OBJECT -> seed_library.db (clean library, canon untouched)

Keys parsed from D:\\Dee_Workspace\\makan.txt (never printed).
Fallback: NVIDIA NIM (OpenAI-compatible) when Gemini exhausted.
"""
import json
import re
import sqlite3
import pathlib
import random
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

CANON = r"D:\object-asset-engine\db\object_asset_engine.db"
LIB = r"D:\object-asset-engine\db\seed_library.db"
MAKAN = pathlib.Path(r"D:\Dee_Workspace\makan.txt")
RUN_LOG = pathlib.Path(r"D:\object-asset-engine\reports\audit_pilot.log")

GEMINI_MODEL = "gemini-3.5-flash-lite"
NVIDIA_MODEL = "nvidia/nemotron-3-super-120b-a12b"
BATCH_SIZE = 1000

SYSTEM_PROMPT = """You are a stock-asset curator. For each seed phrase, decide if it could be sold as an ISOLATED OBJECT illustration (a single drawable thing on a white background) — at ANY scale: macro, microscopic, subatomic (stylized), terrestrial, extraterrestrial or sci-fi/fantasy.

Verdicts:
- "OBJECT" = any physical thing with a distinct visual form, no matter scale or origin: tools, animals, plants, food, vehicles, furniture, devices, clothing, body parts, animal breeds ("german shepherd"), dishes ("french fries"), modern products ("video doorbell"), GENERIC sci-fi/fantasy objects (dragon, potion bottle, alien craft), MICROSCOPIC entities (cells like b lymphocyte / cancer cell / cytosol stylized, molecules like dicumarol / tetraiodothyronine / cytosol, DNA helix), SUBATOMIC stylized (quark, anti-bottom quark as diagram), extraterrestrial objects. If it has a distinct type — even if tiny or stylized/diagram — it is OBJECT. Plural → judge singular.
- "UNSURE" = borderline: bulk materials/substances where object vs mass is ambiguous (gold, sand, gravy as liquid mass, nainsook as fabric), rare-but-real physical things, scenes that might crop into an object. WHEN IN DOUBT, CHOOSE UNSURE — never guess REJECT.
- "REJECT" = clearly NOT an isolated drawable thing: abstract concepts (freedom), actions (running), emotions, time units, places/rooms/buildings (Paris, kitchen, darkroom, offices), professions (banker), real brands (iPhone), events, grammar/linguistic terms, medical conditions as abstract state (tinea as disease), physical properties as abstracts (ferroelectricity as property). NOTE: do NOT REJECT for being microscopic, subatomic, molecule, sci-fi, or extraterrestrial — those are OBJECT if type is distinct.

Rules:
- Judge the THING the word refers to, not its popularity or size.
- Plural forms: judge the singular meaning ("monkeys" = monkey = OBJECT).
- Compound products are OBJECT even if new or uncommon.
- Do NOT reject just because a word is rare, technical, tiny, sci-fi or from space — if it is a distinct physical type, it is OBJECT.
- Chemicals/drugs/molecules: distinct molecule/cell types are OBJECT (stylized structure / pill / vial / diagram are all valid isolated renders). Only REJECT if it is an abstract property, not a substance.
- Genericized trademarks that now mean an object type (barcolounger = recliner chair) = OBJECT.

Output format: one JSON object per line, nothing else:
{"w":"<word>","v":"OBJECT","c":85,"r":"<3-6 word reason>"}
{"w":"<word>","v":"UNSURE","c":60,"r":"..."}
{"w":"<word>","v":"REJECT","c":90,"r":"..."}"""


def parse_keys():
    text = MAKAN.read_text(encoding="utf-8", errors="ignore")
    gemini = [l.strip() for l in text.splitlines() if l.strip().startswith("AQ.")]
    nvidia = [l.strip() for l in text.splitlines()
              if re.match(r"API Key\s*:\s*nvapi-", l.strip())]
    nvidia = [re.sub(r"^API Key\s*:\s*", "", k) for k in nvidia]
    return gemini, nvidia


def call_gemini(key: str, words: list[str]) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={key}")
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": "\n".join(words)}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 65536},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def call_nvidia(key: str, words: list[str]) -> str:
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    body = {
        "model": NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(words)},
        ],
        "temperature": 0.2, "max_tokens": 32768,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def parse_verdicts(text: str, valid_words: set) -> dict:
    out = {}
    for line in text.splitlines():
        line = line.strip().strip("`")
        if not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
            w = str(o.get("w", "")).strip().lower()
            v = str(o.get("v", "")).strip().upper()
            if w in valid_words and v in ("OBJECT", "UNSURE", "REJECT"):
                out[w] = (v, int(o.get("c", 50)), str(o.get("r", ""))[:120])
        except (json.JSONDecodeError, ValueError):
            continue
    return out


def build_pilot_queue(conn):
    n = conn.execute("SELECT COUNT(*) FROM audit_queue").fetchone()[0]
    if n > 0:
        print(f"audit_queue already has {n} rows, skip populate")
        return
    # 500 not_in_wordnet (wave2 reject, score 0.15)
    rows = conn.execute(
        """SELECT canonical_name FROM candidate_seeds
           WHERE wave2_status='reject' AND concreteness_score=0.15
           ORDER BY RANDOM() LIMIT 500""").fetchall()
    for (w,) in rows:
        conn.execute("INSERT OR IGNORE INTO audit_queue(word, source_bucket) VALUES (?, 'not_in_wordnet')", (w,))
    # 300 h4_capital from raw_nouns via filter_log
    rows = conn.execute(
        """SELECT DISTINCT rn.word FROM filter_log f
           JOIN raw_nouns rn ON rn.id = f.raw_noun_id
           WHERE f.filter_rule='H4_ASCII_ONLY' AND f.result='reject'
           ORDER BY RANDOM() LIMIT 300""").fetchall()
    for (w,) in rows:
        conn.execute("INSERT OR IGNORE INTO audit_queue(word, source_bucket) VALUES (?, 'h4_capital')", (w.lower(),))
    # 200 eligible control
    rows = conn.execute(
        """SELECT canonical_name FROM candidate_seeds
           WHERE wave3_status='eligible' ORDER BY RANDOM() LIMIT 200""").fetchall()
    for (w,) in rows:
        conn.execute("INSERT OR IGNORE INTO audit_queue(word, source_bucket) VALUES (?, 'eligible_control')", (w,))
    conn.commit()
    print("pilot queue populated: 500+300+200")


def main() -> None:
    gemini_keys, nvidia_keys = parse_keys()
    print(f"keys loaded: gemini={len(gemini_keys)} nvidia={len(nvidia_keys)}")

    conn = sqlite3.connect(CANON)
    lib = sqlite3.connect(LIB)
    lib.execute("""CREATE TABLE IF NOT EXISTS objects (
        word TEXT PRIMARY KEY, source_bucket TEXT, confidence INTEGER,
        reason TEXT, audited_at TEXT, model TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT UNIQUE, source_bucket TEXT,
        audit_status TEXT DEFAULT 'pending',
        audit_verdict TEXT, audit_confidence INTEGER, audit_reason TEXT,
        audited_at TEXT, model TEXT)""")
    conn.commit()
    build_pilot_queue(conn)

    rows = conn.execute(
        "SELECT word, source_bucket FROM audit_queue WHERE audit_status='pending' LIMIT ?",
        (BATCH_SIZE,)).fetchall()
    words = [r[0] for r in rows]
    buckets = {r[0]: r[1] for r in rows}
    print(f"pilot batch: {len(words)} words")

    text, model_used = None, None
    for i, key in enumerate(gemini_keys):
        try:
            t0 = time.time()
            text = call_gemini(key, words)
            model_used = GEMINI_MODEL
            print(f"gemini key#{i+1} OK in {time.time()-t0:.0f}s")
            break
        except urllib.error.HTTPError as e:
            print(f"gemini key#{i+1} HTTP {e.code}, rotate...")
            time.sleep(3)
        except Exception as e:
            print(f"gemini key#{i+1} ERR {e}, rotate...")
            time.sleep(3)
    if text is None and nvidia_keys:
        for i, key in enumerate(nvidia_keys):
            try:
                t0 = time.time()
                text = call_nvidia(key, words)
                model_used = NVIDIA_MODEL
                print(f"nvidia key#{i+1} OK in {time.time()-t0:.0f}s")
                break
            except Exception as e:
                print(f"nvidia key#{i+1} ERR {e}, rotate...")
                time.sleep(3)
    if text is None:
        print("ALL PROVIDERS FAILED")
        return

    valid = set(words)
    verdicts = parse_verdicts(text, valid)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    by_bucket = {}
    for w, (v, c, r) in verdicts.items():
        conn.execute(
            """UPDATE audit_queue SET audit_status='done', audit_verdict=?,
               audit_confidence=?, audit_reason=?, audited_at=?, model=?
               WHERE word=?""", (v, c, r, now, model_used, w))
        by_bucket.setdefault(buckets[w], {}).setdefault(v, 0)
        by_bucket[buckets[w]][v] += 1
        if v == "OBJECT":
            lib.execute(
                "INSERT OR IGNORE INTO objects VALUES (?,?,?,?,?,?)",
                (w, buckets[w], c, r, now, model_used))
    conn.commit()
    lib.commit()

    missing = len(words) - len(verdicts)
    print(f"\nverdicts parsed: {len(verdicts)}/{len(words)} (missing={missing})")
    print("by bucket:")
    for b, d in sorted(by_bucket.items()):
        print(f"  {b}: {d}")
    print(f"\nseed_library.db objects now: {lib.execute('SELECT COUNT(*) FROM objects').fetchone()[0]}")
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(RUN_LOG, "a", encoding="utf-8") as f:
        f.write(f"{now} pilot done: {len(verdicts)}/{len(words)} model={model_used}\n")
    conn.close()
    lib.close()


if __name__ == "__main__":
    main()
