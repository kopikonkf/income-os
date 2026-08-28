
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-015 — Wave 3 Eligibility Gate (IP/Trademark + Isolated-Object-Suitability).

Spec: Qwen Nouns_Generator6.md.
Input: candidate_seeds WHERE wave2_status IN ('pass','review') -> source_tier tagged.
Gate 3.1: IP/trademark blocklist (exact + contains) + pattern flag.
Gate 3.2: isolated-object suitability via lexname + hypernym path.
Idempotent: processes rows WHERE wave3_status IS NULL/'pending'.
"""
import json
import re
import sqlite3
import pathlib
from datetime import datetime, timezone

from nltk.corpus import wordnet as wn

DB = engine_paths.CANON_DB
BATCH = 10_000

TRADEMARK_BLOCKLIST = {
    # pharma
    "quaaludes", "quaalude", "valium", "xanax", "prozac", "viagra", "roxanol",
    # consumer brands that leak into noun lists
    "band-aid", "band aid", "xerox", "kleenex", "frisbee", "jacuzzi",
    "chapstick", "q-tip", "q tip", "post-it", "post it", "velcro",
    "pyrex", "tupperware", "walkman", "jeep", "aspirin", "heroin",
    "zipper", "thermos", "dungarees", "hula-hoop", "hula hoop",
    "ping-pong", "ping pong", "popsicle", "scotch tape", "dumpster",
    "trampoline", "yoyo", "yo-yo", "kerosene",
    # tech/fictional IP
    "iphone", "ipad", "ipod", "macbook", "playstation", "xbox",
    "nintendo", "lightsaber", "pokeball", "tardis", "batmobile",
    "kryptonite", "lego", "barbie",
}

DISQUALIFY_LEXNAMES = {"noun.location", "noun.person", "noun.group"}
PASS_LEXNAMES = {"noun.artifact", "noun.object", "noun.animal",
                 "noun.plant", "noun.food", "noun.body"}
REVIEW_LEXNAMES = {"noun.substance"}

DISQUALIFY_HYPERNYMS = {
    "location.n.01", "geographical_area.n.01", "region.n.01",
    "person.n.01", "human.n.01", "group.n.01",
    "scene.n.01", "landscape.n.01", "body_of_water.n.01",
    # Wave 3 run-1 findings: WordNet puts landforms under noun.object
    "geological_formation.n.01",
    # art movements / genres are not objects (modernism leak)
    "genre.n.04",
    # mythical beings are humanoid/person-like (blueprint no-human)
    "mythical_being.n.01",
}

# humanoid/fictional-person words (blueprint: no human/humanoid)
HUMANOID_BLOCKLIST = {
    "giant", "ogre", "troll", "gnome", "fairy", "mermaid", "werewolf",
    "zombie", "vampire", "mummy", "wizard", "witch", "leprechaun",
    "goblin", "elf", "imp", "genie", "angel", "demon", "devil",
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


def ip_check(word: str):
    w = word.strip().lower()
    if w in TRADEMARK_BLOCKLIST:
        return "blocked", "known_trademark"
    for t in TRADEMARK_BLOCKLIST:
        if len(t) > 4 and t in w:
            return "blocked", f"contains_trademark:{t}"
    if re.search(r"\d", w) or re.search(r"[^a-z\s\-']", w):
        return "flag", "pattern_nonalpha"
    return "none", ""


def suitability(word: str):
    w = word.strip().lower()
    if w in HUMANOID_BLOCKLIST:
        return "reject", "humanoid_blocklist"
    syns = lookup_synsets(word)
    if not syns:
        return "reject", "not_in_wordnet"
    primary = syns[0]
    lex = primary.lexname()

    if lex in DISQUALIFY_LEXNAMES:
        return "reject", f"lexname={lex}"
    for path in primary.hypernym_paths():
        if {p.name() for p in path} & DISQUALIFY_HYPERNYMS:
            return "reject", "hypernym_disqualifier"
    if lex in PASS_LEXNAMES:
        return "pass", f"lexname={lex}"
    if lex in REVIEW_LEXNAMES:
        return "review", "bulk_substance"
    for path in primary.hypernym_paths():
        if any(p.name() == "physical_entity.n.01" for p in path):
            return "pass", "physical_entity_path"
    return "review", "uncertain"


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(DB)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_seeds)")}
        for col in ("source_tier", "wave3_status"):
            if col not in cols:
                conn.execute(f"ALTER TABLE candidate_seeds ADD COLUMN {col} TEXT")
        if "ip_risk" not in cols:
            conn.execute("ALTER TABLE candidate_seeds ADD COLUMN ip_risk TEXT DEFAULT 'none'")
        if "suitability" not in cols:
            conn.execute("ALTER TABLE candidate_seeds ADD COLUMN suitability TEXT DEFAULT 'pending'")
        conn.execute(
            """UPDATE candidate_seeds SET source_tier = wave2_status,
               wave3_status='pending', ip_risk='none', suitability='pending'
               WHERE wave2_status IN ('pass','review')
                 AND (source_tier IS NULL OR wave3_status IS NULL)"""
            )
        conn.commit()
        n_input = conn.execute(
            "SELECT COUNT(*) FROM candidate_seeds WHERE wave2_status IN ('pass','review')"
        ).fetchone()[0]
        print(f"input rows: {n_input}")

        t0 = datetime.now(timezone.utc)
        counts = {"eligible": 0, "rejected_ip": 0,
                  "rejected_suitability": 0, "review_wave3": 0}
        processed = 0
        samples_eligible = []
        rej_suit_reasons = {}
        while True:
            rows = conn.execute(
                """SELECT id, canonical_name, source_tier FROM candidate_seeds
                   WHERE wave2_status IN ('pass','review')
                     AND (wave3_status='pending' OR wave3_status IS NULL) LIMIT ?""",
                (BATCH,),
            ).fetchall()
            if not rows:
                break
            updates, logs = [], []
            for cid, word, tier in rows:
                ip, ip_detail = ip_check(word)
                if ip == "blocked":
                    w3 = "rejected_ip"
                    suit = "blocked"
                else:
                    suit_r, suit_detail = suitability(word)
                    suit = suit_detail
                    if suit_r == "reject":
                        w3 = "rejected_suitability"
                        rej_suit_reasons[suit_detail.split("=")[-1]] = \
                            rej_suit_reasons.get(suit_detail.split("=")[-1], 0) + 1
                    elif suit_r == "pass" and ip == "none":
                        w3 = "eligible"
                    elif suit_r == "pass" and ip == "flag":
                        w3 = "review_wave3"
                    else:
                        w3 = "review_wave3"
                counts[w3] += 1
                updates.append((ip, suit, w3, now, cid))
                logs.append((cid.replace("CAND-", ""), "wave3",
                             "eligibility", w3,
                             f"{word}: tier={tier} ip={ip}({ip_detail}) suit={suit}"))
                processed += 1
                if w3 == "eligible" and len(samples_eligible) < 40:
                    samples_eligible.append((word, tier, suit))
            conn.executemany(
                """UPDATE candidate_seeds SET ip_risk=?, suitability=?,
                   wave3_status=?, updated_at=? WHERE id=?""",
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
        print("wave3 counts:", counts)

        print("\n-- survival by source_tier --")
        for r in conn.execute(
            """SELECT source_tier, wave3_status, COUNT(*) FROM candidate_seeds
               WHERE source_tier IS NOT NULL GROUP BY source_tier, wave3_status"""
        ):
            print(f"  {r[0]} -> {r[1]}: {r[2]}")

        print("\n-- Gate W3-A: trademarks (expect blocked/rejected_ip) --")
        for r in conn.execute(
            """SELECT canonical_name, ip_risk, wave3_status FROM candidate_seeds
               WHERE canonical_name IN ('quaaludes','band-aid','xerox','jeep',
                                        'velcro','tupperware','lightsaber')"""
        ):
            print(f"  {r[0]}: ip={r[1]} {r[2]}")
        print("\n-- Gate W3-B: places/persons (expect rejected_suitability) --")
        for r in conn.execute(
            """SELECT canonical_name, suitability, wave3_status FROM candidate_seeds
               WHERE canonical_name IN ('coast','mountain','city','giant','banker')"""
        ):
            print(f"  {r[0]}: suit={r[1]} {r[2]}")
        print("\n-- Gate W3-C: objects (expect eligible) --")
        for r in conn.execute(
            """SELECT canonical_name, suitability, wave3_status FROM candidate_seeds
               WHERE canonical_name IN ('butterfly','battle-ax','ankle',
                                        'seismograph','book')"""
        ):
            print(f"  {r[0]}: suit={r[1]} {r[2]}")

        print("\n-- Gate W3-D: 30 random eligible --")
        for r in conn.execute(
            """SELECT canonical_name, source_tier FROM candidate_seeds
               WHERE wave3_status='eligible' ORDER BY RANDOM() LIMIT 30"""
        ):
            print(f"  {r[0]} ({r[1]})")

        print("\n-- top rejection reasons (suitability) --")
        for k, v in sorted(rej_suit_reasons.items(), key=lambda x: -x[1])[:10]:
            print(f"  {k}: {v}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
