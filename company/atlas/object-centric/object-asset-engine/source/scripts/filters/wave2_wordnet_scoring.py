
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-014 — Wave 2 v3 Primary-Decisive Concreteness (re-run, idempotent).

Spec: Qwen Nouns_Generator5.md.
- Primary synset (WordNet corpus-frequency order) DECIDES classification
- Floor 0.70: concrete primary never dragged below pass by abstract secondary
- Gloss keyword matching REMOVED (v1 false-positive source)
- lookup_synsets normalization retained from v2
- Gates A-E verified in output
"""
import json
import sqlite3
import sys
import pathlib
from datetime import datetime, timezone

from nltk.corpus import wordnet as wn

DB = engine_paths.CANON_DB
BATCH = 10_000

CONCRETE_LEXNAMES = {
    "noun.artifact", "noun.object", "noun.animal", "noun.plant",
    "noun.food", "noun.body", "noun.substance", "noun.shape",
}
ABSTRACT_LEXNAMES = {
    "noun.time", "noun.communication", "noun.cognition", "noun.feeling",
    "noun.state", "noun.act", "noun.event", "noun.quantity", "noun.attribute",
    "noun.relation", "noun.possession", "noun.motive", "noun.group",
    "noun.location", "noun.phenomenon", "noun.process", "noun.person",
}


def lookup_synsets(word: str):
    w = word.strip().lower()
    variants = {w, w.replace("-", " "), w.replace("-", ""),
                w.replace(" ", "_"), w.replace("-", "_")}
    syns = []
    for v in variants:
        syns.extend(wn.synsets(v, pos="n"))
        if len(syns) >= 20:
            break
    return list(dict.fromkeys(syns))


def classify(syn) -> str:
    lex = syn.lexname()
    if lex in CONCRETE_LEXNAMES:
        return "concrete"
    if lex in ABSTRACT_LEXNAMES:
        return "abstract"
    if lex == "noun.Tops":
        return "generic"
    return "other"


def has_physical_path(syn) -> bool:
    for path in syn.hypernym_paths():
        if any(p.name() == "physical_entity.n.01" for p in path):
            return True
    return False


def score_concreteness_v3(word: str) -> dict:
    syns = lookup_synsets(word)
    if not syns:
        return {"score": 0.15, "action": "reject",
                "reason": "not_in_wordnet", "synsets": []}

    primary = syns[0]
    secondary = syns[1:]

    pc = classify(primary)
    p_phys = has_physical_path(primary)
    sec_conc = sum(1 for s in secondary if classify(s) == "concrete")

    if pc == "concrete":
        score = 0.75
        if p_phys:
            score += 0.10
        if sec_conc:
            score += min(0.05 * sec_conc, 0.10)
        score = max(score, 0.70)
    elif pc == "abstract":
        score = 0.45 if sec_conc else 0.15
    elif pc == "generic":
        score = 0.45 if (sec_conc or p_phys) else 0.30
    else:
        if p_phys:
            score = 0.60
        elif sec_conc:
            score = 0.45
        else:
            score = 0.35

    score = max(0.05, min(0.95, score))
    action = "pass" if score >= 0.55 else ("review" if score >= 0.40 else "reject")

    return {"score": round(score, 3), "action": action,
            "reason": f"primary={pc},phys={p_phys},sec_conc={sec_conc},total={len(syns)}",
            "synsets": [s.name() for s in syns[:8]]}


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(DB)
    try:
        if "--no-reset" not in sys.argv:
            conn.execute(
                """UPDATE candidate_seeds SET wave2_status='pending',
                   concreteness_score=0, wordnet_synsets='[]'
                   WHERE wave1_status='pass'"""
            )
            conn.commit()
            print("reset wave2 fields for v3 re-run")

        t0 = datetime.now(timezone.utc)
        counts = {"pass": 0, "review": 0, "reject": 0}
        processed = 0
        samples = {"pass": [], "reject": [], "review": []}
        while True:
            rows = conn.execute(
                """SELECT id, canonical_name FROM candidate_seeds
                   WHERE wave1_status='pass' AND wave2_status='pending' LIMIT ?""",
                (BATCH,),
            ).fetchall()
            if not rows:
                break
            updates, logs = [], []
            for cid, word in rows:
                r = score_concreteness_v3(word)
                counts[r["action"]] += 1
                updates.append((r["action"], r["score"], json.dumps(r["synsets"]), now, cid))
                logs.append((cid.replace("CAND-", ""), "wave2v3", "primary_decisive",
                             r["action"], f"{word}: {r['reason']} score={r['score']}"))
                processed += 1
                if r["action"] in samples and len(samples[r["action"]]) < 30:
                    samples[r["action"]].append((word, r["score"], r["reason"]))
            conn.executemany(
                """UPDATE candidate_seeds SET wave2_status=?, concreteness_score=?,
                   wordnet_synsets=?, updated_at=? WHERE id=?""",
                updates,
            )
            conn.executemany(
                """INSERT INTO filter_log (raw_noun_id, filter_wave, filter_rule, result, detail)
                   VALUES (?, ?, ?, ?, ?)""",
                logs,
            )
            conn.commit()
            if processed // 50_000 != (processed - len(rows)) // 50_000:
                print(f"progress processed={processed} {counts} "
                      f"elapsed={(datetime.now(timezone.utc)-t0).seconds}s", flush=True)

        elapsed = (datetime.now(timezone.utc) - t0).seconds
        print(f"DONE processed={processed} elapsed={elapsed}s")
        print("wave2v3 counts:", counts)

        print("\n-- Gate A: v1 FPs (expect reject) --")
        for r in conn.execute(
            """SELECT canonical_name, wave2_status, concreteness_score
               FROM candidate_seeds WHERE canonical_name IN
               ('nonsense','day','hour','name','fable')"""
        ):
            print(f"  {r[0]}: {r[1]} ({r[2]})")
        print("\n-- Gate B: polysemy recovery (expect pass; book pass/review) --")
        for r in conn.execute(
            """SELECT canonical_name, wave2_status, concreteness_score
               FROM candidate_seeds WHERE canonical_name IN
               ('elephant','crow','pie','book')"""
        ):
            print(f"  {r[0]}: {r[1]} ({r[2]})")
        print("\n-- Gate C --")
        for r in conn.execute(
            """SELECT canonical_name, wave2_status, concreteness_score
               FROM candidate_seeds WHERE canonical_name IN
               ('aardvark','aard-vark','trade wind')"""
        ):
            print(f"  {r[0]}: {r[1]} ({r[2]})")

        # Gate E: v2 reject -> v3 pass delta via filter_log join
        print("\n-- Gate E: 20 sample v2-reject -> v3-pass delta --")
        q = """
        SELECT c.canonical_name, c.concreteness_score, c.wordnet_synsets
        FROM candidate_seeds c
        WHERE c.wave2_status='pass' AND EXISTS (
            SELECT 1 FROM filter_log f2 WHERE f2.raw_noun_id = c.raw_noun_id
              AND f2.filter_wave='wave2v2' AND f2.result='reject')
          AND EXISTS (
            SELECT 1 FROM filter_log f3 WHERE f3.raw_noun_id = c.raw_noun_id
              AND f3.filter_wave='wave2v3' AND f3.result='pass')
        ORDER BY RANDOM() LIMIT 20
        """
        delta = conn.execute(q).fetchall()
        for r in delta:
            print(f"  {r[0]} ({r[1]}) {r[2][:60]}")
        total_delta = conn.execute(
            """
            SELECT COUNT(*) FROM candidate_seeds c
            WHERE c.wave2_status='pass' AND EXISTS (
                SELECT 1 FROM filter_log f2 WHERE f2.raw_noun_id=c.raw_noun_id
                  AND f2.filter_wave='wave2v2' AND f2.result='reject')
              AND EXISTS (
                SELECT 1 FROM filter_log f3 WHERE f3.raw_noun_id=c.raw_noun_id
                  AND f3.filter_wave='wave2v3' AND f3.result='pass')
            """
        ).fetchone()[0]
        print(f"  total delta (v2 reject -> v3 pass): {total_delta}")

        print("\n-- Gate D: 30 random pass --")
        for r in conn.execute(
            """SELECT canonical_name, concreteness_score FROM candidate_seeds
               WHERE wave2_status='pass' ORDER BY RANDOM() LIMIT 30"""
        ):
            print(f"  {r[0]} ({r[1]})")

        print("\n-- score stats --")
        for r in conn.execute(
            """SELECT MIN(concreteness_score), MAX(concreteness_score),
                      AVG(concreteness_score), COUNT(*)
               FROM candidate_seeds WHERE wave2_status != 'pending'"""
        ):
            print(f"  min={r[0]} max={r[1]} avg={round(r[2],3)} total={r[3]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
