
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-AUDIT-002 — Scale worker for 755k audit (gemini-3.5-flash-lite, 7-key rotation).

Usage:
  py gemini_audit_scale.py --populate          # enqueue 755k (idempotent, INSERT OR IGNORE)
  py gemini_audit_scale.py --run               # process pending forever (batch 1000, rotate keys)
  py gemini_audit_scale.py --run --batches 5   # process 5 batches then exit (testing)
  py gemini_audit_scale.py --status             # show progress
  py gemini_audit_scale.py --resume             # same as --run but verbose resume info

Features:
  - 7 Gemini keys rotation, per-key 429 backoff (30s), global fallback to next key.
  - Checkpoint per batch: update audit_queue + seed_library.db commit.
  - Rate limit throttle: 2s between calls + jitter.
  - Handles single pending mcjobs that was missed in pilot (parser edge).
  - Logs to reports/audit_scale.log
"""
import argparse
import json
import pathlib
import random
import re
import sqlite3
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from collections import Counter

CANON = str(engine_paths.CANON_DB)
LIB = str(engine_paths.SEED_LIBRARY_DB)
MAKAN = None
RUN_LOG = engine_paths.REPORTS_DIR / "audit_scale.log"

GEMINI_MODEL = "gemini-3.5-flash-lite"
BATCH_SIZE = 500  # 500 fits 16k token limit; 1000 truncates at 16k (see test_500_timing.py 30s/500 vs 40s/1000 truncated)
SLEEP_BETWEEN_BATCHES = 5  # seconds (2026-08-28 user request: 30s → 5s, hemat 5.4 jam; per-key 19.7 menit vs 22.6 menit, tetap aman 429)

# Prompt is imported from gemini_audit_worker.py to keep single source
import importlib.util, sys
spec = importlib.util.spec_from_file_location("worker", str(pathlib.Path(__file__).parent / "gemini_audit_worker.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SYSTEM_PROMPT = mod.SYSTEM_PROMPT


def parse_keys():
    text = engine_paths.require_gemini_key_file().read_text(encoding="utf-8", errors="ignore")
    gemini = [l.strip() for l in text.splitlines() if l.strip().startswith("AQ.")]
    return gemini


def call_gemini(key: str, words: list[str]) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}"
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": "\n".join(words)}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 65536},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode())
    return data["candidates"][0]["content"]["parts"][0]["text"]


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


def ensure_tables():
    conn = sqlite3.connect(CANON)
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT UNIQUE, source_bucket TEXT,
        audit_status TEXT DEFAULT 'pending',
        audit_verdict TEXT, audit_confidence INTEGER, audit_reason TEXT,
        audited_at TEXT, model TEXT)""")
    conn.commit()
    lib = sqlite3.connect(LIB)
    lib.execute("""CREATE TABLE IF NOT EXISTS objects (
        word TEXT PRIMARY KEY, source_bucket TEXT, confidence INTEGER,
        reason TEXT, audited_at TEXT, model TEXT)""")
    lib.commit()
    conn.close()
    lib.close()


def populate():
    """Populate audit_queue with full 755k (idempotent)."""
    conn = sqlite3.connect(CANON)
    ensure_tables()
    # Count existing
    existing = conn.execute("SELECT COUNT(*) FROM audit_queue").fetchone()[0]
    print(f"[populate] existing audit_queue rows: {existing}")

    # 1) not_in_wordnet: candidate_seeds wave2_status reject + concreteness 0.15
    print("[populate] inserting not_in_wordnet ...")
    conn.execute("""
        INSERT OR IGNORE INTO audit_queue(word, source_bucket)
        SELECT canonical_name, 'not_in_wordnet' FROM candidate_seeds
        WHERE wave2_status='reject' AND concreteness_score=0.15
    """)
    conn.commit()
    n1 = conn.execute("SELECT COUNT(*) FROM audit_queue WHERE source_bucket='not_in_wordnet'").fetchone()[0]
    print(f"  not_in_wordnet now: {n1}")

    # 2) h4_capital: distinct raw_nouns that failed H4
    print("[populate] inserting h4_capital (may take 10-20s) ...")
    conn.execute("""
        INSERT OR IGNORE INTO audit_queue(word, source_bucket)
        SELECT lower(rn.word), 'h4_capital' FROM filter_log f
        JOIN raw_nouns rn ON rn.id = f.raw_noun_id
        WHERE f.filter_rule='H4_ASCII_ONLY' AND f.result='reject'
        GROUP BY lower(rn.word)
    """)
    conn.commit()
    n2 = conn.execute("SELECT COUNT(*) FROM audit_queue WHERE source_bucket='h4_capital'").fetchone()[0]
    print(f"  h4_capital now: {n2}")

    total = conn.execute("SELECT COUNT(*) FROM audit_queue").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM audit_queue WHERE audit_status='pending'").fetchone()[0]
    print(f"[populate] total={total} pending={pending} done={total-pending}")
    print(f"[populate] batches needed: {(pending + BATCH_SIZE -1)//BATCH_SIZE} x {BATCH_SIZE}")
    # Estimate hours
    est_min = (pending / BATCH_SIZE) * 2.0  # 2 min per batch avg with 3.5-flash-lite
    print(f"[populate] est single-key: {est_min/60:.1f}h, 7-key parallel ideal: {est_min/60/7:.1f}h, @3.4min/batch: {(pending/BATCH_SIZE)*3.4/60:.1f}h")
    conn.close()


def status():
    conn = sqlite3.connect(CANON)
    lib = sqlite3.connect(LIB)
    total = conn.execute("SELECT COUNT(*) FROM audit_queue").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM audit_queue WHERE audit_status='pending'").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM audit_queue WHERE audit_status='done'").fetchone()[0]
    print(f"audit_queue: total={total} done={done} pending={pending}")
    for row in conn.execute("SELECT audit_verdict, COUNT(*) FROM audit_queue WHERE audit_verdict IS NOT NULL GROUP BY audit_verdict").fetchall():
        print(f"  verdict {row[0]}: {row[1]}")
    for row in conn.execute("SELECT source_bucket, audit_verdict, COUNT(*) FROM audit_queue WHERE audit_verdict IS NOT NULL GROUP BY source_bucket, audit_verdict ORDER BY source_bucket").fetchall():
        print(f"  {row[0]} {row[1]}: {row[2]}")
    try:
        lib_count = lib.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
        print(f"seed_library.objects: {lib_count}")
    except: pass
    # Last log tail
    if RUN_LOG.exists():
        lines = RUN_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
        print(f"\nlast 5 log lines:")
        for l in lines[-5:]:
            print(f"  {l}")
    conn.close()
    lib.close()


def run_loop(max_batches: int = None):
    gemini_keys = parse_keys()
    print(f"keys loaded: gemini={len(gemini_keys)} model={GEMINI_MODEL}")
    ensure_tables()

    conn = sqlite3.connect(CANON, timeout=30)
    lib = sqlite3.connect(LIB, timeout=30)

    # Round-robin index based on done count to spread load
    total_done = conn.execute("SELECT COUNT(*) FROM audit_queue WHERE audit_status='done'").fetchone()[0]
    key_idx = total_done % len(gemini_keys) if gemini_keys else 0

    batches_done = 0
    consecutive_failures = 0

    while True:
        if max_batches and batches_done >= max_batches:
            print(f"[run] reached max_batches={max_batches}, exit")
            break

        rows = conn.execute(
            "SELECT word, source_bucket FROM audit_queue WHERE audit_status='pending' LIMIT ?",
            (BATCH_SIZE,)).fetchall()
        if not rows:
            print("[run] no pending rows, all done!")
            break

        words = [r[0] for r in rows]
        buckets = {r[0]: r[1] for r in rows}
        pending_before = conn.execute("SELECT COUNT(*) FROM audit_queue WHERE audit_status='pending'").fetchone()[0]
        print(f"\n[run] batch {batches_done+1}: {len(words)} words (pending before: {pending_before})")

        text, model_used, used_key_idx = None, None, None
        # Try each key rotating from key_idx
        for attempt in range(len(gemini_keys)):
            ki = (key_idx + attempt) % len(gemini_keys)
            key = gemini_keys[ki]
            try:
                t0 = time.time()
                text = call_gemini(key, words)
                elapsed = time.time() - t0
                model_used = GEMINI_MODEL
                used_key_idx = ki
                print(f"  key#{ki+1} OK in {elapsed:.1f}s (chars={len(text)})")
                consecutive_failures = 0
                key_idx = (ki + 1) % len(gemini_keys)  # rotate for next batch
                break
            except urllib.error.HTTPError as e:
                body = ""
                try: body = e.read().decode()[:300]
                except: pass
                print(f"  key#{ki+1} HTTP {e.code}: {body[:150]} -> rotate")
                if e.code == 429:
                    print(f"    rate-limited, sleep 30s before next key")
                    time.sleep(30)
                else:
                    time.sleep(3)
            except Exception as e:
                print(f"  key#{ki+1} ERR {e} -> rotate")
                time.sleep(3)

        if text is None:
            consecutive_failures += 1
            print(f"[run] ALL KEYS FAILED for this batch ({consecutive_failures} consecutive)")
            if consecutive_failures >= 3:
                print("[run] too many consecutive failures, sleep 60s then retry same batch")
                time.sleep(60)
            else:
                time.sleep(10)
            continue

        valid = set(w.lower() for w in words)  # normalize
        # parse is lowercased w, so match lower
        verdicts = parse_verdicts(text, valid)
        # Also try case-sensitive fallback for words that were not lower (shouldn't happen)
        if len(verdicts) < len(words) * 0.8:
            # Debug: log raw
            print(f"  parse low: {len(verdicts)}/{len(words)} - raw preview: {text[:500]!r}")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        by_bucket = Counter()
        by_verdict = Counter()
        for w_lower, (v, c, r) in verdicts.items():
            # find original word with that lower
            orig_word = next((w for w in words if w.lower() == w_lower), w_lower)
            bucket = buckets.get(orig_word, buckets.get(w_lower, "unknown"))
            conn.execute(
                """UPDATE audit_queue SET audit_status='done', audit_verdict=?,
                   audit_confidence=?, audit_reason=?, audited_at=?, model=?
                   WHERE lower(word)=?""", (v, c, r, now, model_used, w_lower))
            by_verdict[v] += 1
            by_bucket[bucket + ":" + v] += 1
            if v == "OBJECT":
                lib.execute(
                    "INSERT OR IGNORE INTO objects VALUES (?,?,?,?,?,?)",
                    (orig_word.lower(), bucket, c, r, now, model_used))
        conn.commit()
        lib.commit()

        # Handle missing (no verdict) -> mark as unsure? Keep pending for retry? For now mark UNSURE to avoid stall
        missing = len(words) - len(verdicts)
        if missing > 0:
            print(f"  missing {missing} words, marking as pending retry (will retry next loop)")
            # Do not mark done; leave pending so retry with different key/prompt might succeed
            # But if missing is large (>20%), log raw to file
            if missing > len(words) * 0.2:
                miss_file = engine_paths.REPORTS_DIR / "audit_miss_batches"
                miss_file.mkdir(parents=True, exist_ok=True)
                with open(miss_file / f"miss_{now.replace(':','-')}.txt", "w", encoding="utf-8") as f:
                    f.write(text[:20000])

        print(f"  verdicts: {dict(by_verdict)} missing={missing}")
        print(f"  by bucket: {dict(by_bucket)}")
        pending = conn.execute("SELECT COUNT(*) FROM audit_queue WHERE audit_status='pending'").fetchone()[0]
        lib_cnt = lib.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
        print(f"  queue remaining: {pending} | seed_library: {lib_cnt}")

        RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(RUN_LOG, "a", encoding="utf-8") as f:
            f.write(f"{now} batch {batches_done+1}: {len(verdicts)}/{len(words)} {dict(by_verdict)} pending={pending} model={model_used} key#{used_key_idx+1}\n")

        batches_done += 1
        time.sleep(SLEEP_BETWEEN_BATCHES + random.uniform(0, 1))

    conn.close()
    lib.close()
    print(f"\n[run] finished batches_done={batches_done}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--populate", action="store_true", help="populate audit_queue to 755k")
    ap.add_argument("--run", action="store_true", help="run processing loop")
    ap.add_argument("--status", action="store_true", help="show status")
    ap.add_argument("--resume", action="store_true", help="alias for --run")
    ap.add_argument("--batches", type=int, default=None, help="max batches to run")
    args = ap.parse_args()
    if args.populate:
        populate()
    elif args.status:
        status()
    elif args.run or args.resume:
        run_loop(max_batches=args.batches)
    else:
        ap.print_help()
