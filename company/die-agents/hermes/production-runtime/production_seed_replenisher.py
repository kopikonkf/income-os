#!/usr/bin/env python3
"""Bounded demand/opportunity replenishment for the DIE production seed pool.

This module promotes only pre-cleaned Wave-3 candidates. It never claims exact
noun transaction/search-volume validation: direct terms carry observed term
presence from the pinned research snapshot; all other promoted terms carry only
category-level composable-raster utility evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from production_seed_selector import produced_seed_ids

SCHEMA = "die.production-seed-replenishment.v1"
DEFAULT_DB = Path("/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db")
DEFAULT_WORKSPACES = Path("/var/lib/die/workspaces")
DEFAULT_POLICY = Path(__file__).with_name("production_seed_replenishment_policy.v1.json")
DEFAULT_STATE = Path("/var/lib/die/state/production-runtime/replenishment")
SEED_RE = re.compile(r"^SEED-(\d{6})$")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def csha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_policy(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "die.production.seed-replenishment-policy.v1":
        raise RuntimeError("E_POLICY_SCHEMA")
    if int(value["low_watermark"]) < 1 or int(value["target_pool_size"]) <= int(value["low_watermark"]):
        raise RuntimeError("E_POLICY_WATERMARK")
    if int(value["max_promotions_per_run"]) < 1:
        raise RuntimeError("E_POLICY_PROMOTION_LIMIT")
    return value


def _norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).split())


def _represented(candidate_name: str, seed_names: list[str]) -> bool:
    c = _norm(candidate_name)
    if not c:
        return True
    c_words = c.split()
    for raw in seed_names:
        s = _norm(raw)
        if c == s:
            return True
        # Multiword candidate already embedded in a richer legacy seed is the
        # same noun family for replenishment purposes (e.g. coffee cup).
        if len(c_words) >= 2 and re.search(r"(?:^|\s)" + re.escape(c) + r"(?:$|\s)", s):
            return True
    return False


def _eligible_seed_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT id, canonical_name, demand_score, demand_status
          FROM seeds
         WHERE status='approved'
           AND asset_tier='U1-raster'
           AND demand_status IN ('validated_high','validated_medium')
         ORDER BY id
        """
    ).fetchall()


def _remaining(connection: sqlite3.Connection, used: set[str]) -> list[sqlite3.Row]:
    return [row for row in _eligible_seed_rows(connection) if str(row["id"]) not in used]


def _candidate_rows(connection: sqlite3.Connection, policy: dict[str, Any]) -> list[sqlite3.Row]:
    gate = policy["candidate_gate"]
    allowed = list(gate["allowed_suitability"])
    qmarks = ",".join("?" for _ in allowed)
    return connection.execute(
        f"""
        SELECT id, canonical_name, aliases, word_count, concreteness_score,
               suitability, ip_risk, source_tier, wave3_status, promoted_to_seed_id
          FROM candidate_seeds
         WHERE wave3_status=?
           AND source_tier=?
           AND ip_risk=?
           AND promoted_to_seed_id IS NULL
           AND concreteness_score>=?
           AND word_count<=?
           AND suitability IN ({qmarks})
        """,
        (
            gate["wave3_status"], gate["source_tier"], gate["ip_risk"],
            float(gate["min_concreteness_score"]), int(gate["max_word_count"]), *allowed,
        ),
    ).fetchall()


def _ranked_candidates(connection: sqlite3.Connection, policy: dict[str, Any]) -> list[dict[str, Any]]:
    direct = [_norm(x) for x in policy["direct_terms"]]
    utility = [_norm(x) for x in policy["utility_terms"]]
    direct_rank = {name: i for i, name in enumerate(direct)}
    util_rank = {name: i for i, name in enumerate(utility)}
    policy_names = set(direct_rank) | set(util_rank)
    seed_names = [str(r[0]) for r in connection.execute("SELECT canonical_name FROM seeds")]
    rows: list[dict[str, Any]] = []
    for row in _candidate_rows(connection, policy):
        name = _norm(row["canonical_name"])
        if name not in policy_names or _represented(str(row["canonical_name"]), seed_names):
            continue
        evidence_level = "DIRECT_TERM_OBSERVED" if name in direct_rank else "CATEGORY_LEVEL_COMPOSABLE_RASTER"
        rank_group = 0 if evidence_level == "DIRECT_TERM_OBSERVED" else 1
        rank = direct_rank.get(name, util_rank.get(name, 10**6))
        rows.append({"row": row, "evidence_level": evidence_level, "rank_group": rank_group, "policy_rank": rank})
    rows.sort(key=lambda x: (x["rank_group"], x["policy_rank"], -float(x["row"]["concreteness_score"]), str(x["row"]["canonical_name"])))
    return rows


def _score(row: sqlite3.Row, evidence_level: str, policy: dict[str, Any]) -> tuple[float, str, str]:
    scoring = policy["scoring"]
    direct = evidence_level == "DIRECT_TERM_OBSERVED"
    base = float(scoring["direct_base"] if direct else scoring["category_base"])
    concrete = float(row["concreteness_score"])
    bonus_span = max(0.0, min(1.0, (concrete - float(policy["candidate_gate"]["min_concreteness_score"])) / 0.10))
    score = base + float(scoring["concreteness_bonus_max"]) * bonus_span
    if not direct:
        score += float(scoring["class_bonus"].get(str(row["suitability"]), 0.0))
    score = round(max(0.0, min(1.0, score)), 3)
    if score >= float(scoring["validated_high_threshold"]):
        status = "validated_high"
    elif score >= float(scoring["validated_medium_threshold"]):
        status = "validated_medium"
    else:
        raise RuntimeError(f"E_SCORE_BELOW_PRODUCTION_GATE:{row['canonical_name']}:{score}")
    signal = "REPLENISH_DIRECT_TERM" if direct else "REPLENISH_CATEGORY_LEVEL"
    return score, status, signal


def _next_seed_number(connection: sqlite3.Connection) -> int:
    highest = 0
    for (seed_id,) in connection.execute("SELECT id FROM seeds"):
        match = SEED_RE.fullmatch(str(seed_id))
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _expression(candidate_id: str, noun: str, policy: dict[str, Any]) -> tuple[str, str]:
    mode = policy["expression"]["mode"]
    expression_id = "EXPR-" + hashlib.sha256(f"{candidate_id}|{mode}".encode()).hexdigest()[:16].upper()
    text = str(policy["expression"]["template"]).format(noun=noun)
    return expression_id, text


def _assert_no_pending_receipt(state_root: Path) -> None:
    if not state_root.exists():
        return
    if not state_root.is_dir():
        raise RuntimeError(f"E_REPLENISHMENT_STATE_ROOT_NOT_DIRECTORY:{state_root}")
    for path in sorted(state_root.glob("REPLENISH-*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("schema") == SCHEMA and value.get("status") == "PENDING_DB_COMMIT":
            raise RuntimeError(f"E_PENDING_REPLENISHMENT_RECEIPT:{path}")


def replenish_seed_pool(
    db_path: Path = DEFAULT_DB,
    workspaces_root: Path = DEFAULT_WORKSPACES,
    *,
    policy_path: Path = DEFAULT_POLICY,
    state_root: Path = DEFAULT_STATE,
    dry_run: bool = False,
) -> dict[str, Any]:
    policy = load_policy(policy_path)
    _assert_no_pending_receipt(state_root)
    used = produced_seed_ids(workspaces_root)
    connection = sqlite3.connect(str(db_path), timeout=30)
    connection.row_factory = sqlite3.Row
    intent_path: Path | None = None
    intent: dict[str, Any] | None = None
    committed = False
    try:
        remaining_before = _remaining(connection, used)
        low = int(policy["low_watermark"])
        target = int(policy["target_pool_size"])
        max_promotions = int(policy["max_promotions_per_run"])
        if len(remaining_before) >= low:
            return {
                "schema": SCHEMA, "status": "NOOP_POOL_HEALTHY", "policy_revision": policy["revision"],
                "remaining_before": len(remaining_before), "remaining_after": len(remaining_before),
                "promoted_count": 0, "promoted": [], "provider_call_performed": False,
                "authority_effect": "NONE",
            }

        need = min(max(0, target - len(remaining_before)), max_promotions)
        ranked = _ranked_candidates(connection, policy)
        selected = ranked[:need]
        planned = []
        next_num = _next_seed_number(connection)
        for offset, item in enumerate(selected):
            row = item["row"]
            score, dstatus, signal = _score(row, item["evidence_level"], policy)
            seed_id = f"SEED-{next_num + offset:06d}"
            expr_id, expr = _expression(str(row["id"]), str(row["canonical_name"]), policy)
            planned.append({
                "candidate_id": str(row["id"]), "seed_id": seed_id, "expression_id": expr_id,
                "canonical_name": str(row["canonical_name"]), "commercial_expression": expr,
                "evidence_level": item["evidence_level"], "opportunity_score": score,
                "demand_status": dstatus, "demand_signal": signal,
                "concreteness_score": float(row["concreteness_score"]), "suitability": str(row["suitability"]),
            })

        if not planned:
            return {
                "schema": SCHEMA, "status": "NO_PROMOTABLE_CANDIDATE", "policy_revision": policy["revision"],
                "remaining_before": len(remaining_before), "remaining_after": len(remaining_before),
                "promoted_count": 0, "promoted": [], "provider_call_performed": False,
                "authority_effect": "NONE", "next_action": "EXPAND_VERSIONED_REPLENISHMENT_EVIDENCE_POLICY",
            }
        if dry_run:
            return {
                "schema": SCHEMA, "status": "DRY_RUN", "policy_revision": policy["revision"],
                "remaining_before": len(remaining_before), "target_pool_size": target,
                "planned_count": len(planned), "planned": planned,
                "provider_call_performed": False, "authority_effect": "NONE",
            }

        created = now()
        run_id = "REPLENISH-" + created.replace(":", "").replace("-", "")
        intent_path = state_root / f"{run_id}.json"
        intent = {
            "schema": SCHEMA, "status": "PENDING_DB_COMMIT", "run_id": run_id,
            "policy_revision": policy["revision"], "policy_sha256": csha(policy),
            "remaining_before": len(remaining_before), "target_pool_size": target,
            "planned_count": len(planned), "planned": planned,
            "truth_boundary": policy["evidence"]["truth_boundary"],
            "provider_call_performed": False, "authority": policy["authority"],
            "created_at": created,
        }
        # Audit intent must be durable before any Object Atlas mutation.
        atomic_json(intent_path, intent)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS production_seed_expressions (
              expression_id TEXT PRIMARY KEY,
              seed_id TEXT NOT NULL UNIQUE,
              candidate_id TEXT NOT NULL UNIQUE,
              commercial_expression TEXT NOT NULL,
              evidence_level TEXT NOT NULL,
              evidence_ref TEXT NOT NULL,
              opportunity_score REAL NOT NULL,
              policy_revision TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """
        )
        # Re-check candidate promotion state inside the write transaction.
        for item in planned:
            current = connection.execute("SELECT promoted_to_seed_id FROM candidate_seeds WHERE id=?", (item["candidate_id"],)).fetchone()
            if current is None or current[0] is not None:
                raise RuntimeError(f"E_CANDIDATE_PROMOTION_RACE:{item['candidate_id']}")
            row = connection.execute("SELECT aliases FROM candidate_seeds WHERE id=?", (item["candidate_id"],)).fetchone()
            category = "object_atlas." + item["suitability"].split("=", 1)[-1].replace("noun.", "")
            connection.execute(
                """
                INSERT INTO seeds (
                  id,canonical_name,aliases,object_class,existence_type,category_path,
                  visuality_score,demand_score,risk_score,status,created_at,updated_at,
                  canonical_lang,asset_tier,source_batch,master_source_id,demand_signal,demand_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    item["seed_id"], item["canonical_name"], row[0] if row else "[]", "concrete_visual", "real_world", category,
                    item["concreteness_score"], item["opportunity_score"], 0.0, "approved", created, created,
                    "en-US", "U1-raster", "PROD-SEED-REPLENISH-V1", item["expression_id"], item["demand_signal"], item["demand_status"],
                ),
            )
            connection.execute(
                """
                INSERT INTO production_seed_expressions (
                  expression_id,seed_id,candidate_id,commercial_expression,evidence_level,
                  evidence_ref,opportunity_score,policy_revision,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    item["expression_id"], item["seed_id"], item["candidate_id"], item["commercial_expression"],
                    item["evidence_level"], policy["evidence"]["source_title"], item["opportunity_score"], policy["revision"], created,
                ),
            )
            connection.execute(
                "UPDATE candidate_seeds SET promoted_to_seed_id=?, status='promoted', updated_at=? WHERE id=?",
                (item["seed_id"], created, item["candidate_id"]),
            )
        connection.commit()
        committed = True

        remaining_after = _remaining(connection, used)
        receipt = {
            "schema": SCHEMA, "status": "PROMOTED", "run_id": run_id,
            "policy_revision": policy["revision"], "policy_sha256": csha(policy),
            "remaining_before": len(remaining_before), "remaining_after": len(remaining_after),
            "target_pool_size": target, "promoted_count": len(planned), "promoted": planned,
            "truth_boundary": policy["evidence"]["truth_boundary"],
            "provider_call_performed": False, "authority": policy["authority"],
            "created_at": created, "committed_at": now(),
        }
        atomic_json(intent_path, receipt)
        receipt["receipt_path"] = str(intent_path)
        return receipt
    except Exception as exc:
        if connection.in_transaction:
            connection.rollback()
        if intent_path is not None and intent is not None and not committed:
            try:
                rolled = dict(intent)
                rolled.update({"status": "ROLLED_BACK", "error": type(exc).__name__, "message": str(exc)[:500], "rolled_back_at": now()})
                atomic_json(intent_path, rolled)
            except Exception:
                pass
        raise
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("DIE_OBJECT_ATLAS_DB", DEFAULT_DB)))
    parser.add_argument("--workspaces", type=Path, default=Path(os.environ.get("DIE_WORKSPACES_ROOT", DEFAULT_WORKSPACES)))
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = replenish_seed_pool(args.db, args.workspaces, policy_path=args.policy, state_root=args.state_root, dry_run=args.dry_run)
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "BLOCKED", "error": type(exc).__name__, "message": str(exc)[:1000]}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())