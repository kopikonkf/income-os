"""DIE platform outcome receipt ingestion v1.

Validates a candidate JSON file against
company/schemas/die.platform.receipt.v1.schema.json, stores the immutable
copy under state/operator/platform_receipts/<receipt_id>.json, and records
one NOTICE event through bin/die_event.py.

Subcommands:
  ingest --file PATH          validate + store + emit event
  list                        summarize stored receipts

Founder supplies receipt JSON files manually in V0 (submission is manual).
Synthetic receipts are permitted for simulation only and must carry
evidence_label=SYNTHETIC with recorded_by=simulation-fixture and cost 0
(enforced by the schema's conditional).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))
from income_os_bridge import config as die_config

DIE = die_config.DIE_HOME
RECEIPTS = die_config.STATE / "operator" / "platform_receipts"
SCHEMA = DIE / "company" / "schemas" / "die.platform.receipt.v1.schema.json"
EVENT_PY = DIE / "bin" / "die_event.py"


def clean_env():
    env = dict(os.environ)
    for key in list(env):
        if any(x in key.upper() for x in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")):
            env.pop(key, None)
    return env


def validate(instance: dict) -> list:
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema module unavailable; cannot validate"]
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"schema unreadable: {exc}"]
    validator = jsonschema.Draft202012Validator(schema)
    return [e.message for e in sorted(validator.iter_errors(instance), key=lambda e: e.path)]


def cmd_ingest(args) -> int:
    source = pathlib.Path(args.file).resolve()
    try:
        instance = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INGEST_REJECTED: unreadable file: {exc}", file=sys.stderr)
        return 2
    errors = validate(instance if isinstance(instance, dict) else {})
    if errors:
        print("INGEST_REJECTED:")
        for err in errors:
            print(f"  - {err}")
        return 1
    receipt_id = instance["receipt_id"]
    if not re.fullmatch(r"PLATREC-[A-Z0-9_-]{8,100}", receipt_id):
        print(f"INGEST_REJECTED: bad receipt_id {receipt_id!r}")
        return 1
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    target = RECEIPTS / f"{receipt_id}.json"
    if target.exists() and target.read_text(encoding="utf-8") == json.dumps(
            instance, ensure_ascii=False, indent=2) + "\n":
        print(f"INGEST_IDEMPOTENT: {receipt_id} already stored")
        return 0
    target.write_text(json.dumps(instance, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    summary = (f"platform receipt {receipt_id}: {instance.get('asset_id')} "
               f"{instance.get('platform')} {instance.get('stage')} "
               f"{instance.get('outcome')} reason={instance.get('reason_code')} "
               f"label={instance.get('evidence_label')}")
    cmd = [
        sys.executable, str(EVENT_PY), "event",
        "--class", "NOTICE", "--source", "platform-receipt-ingestor",
        "--summary", summary[:140], "--mission-id", "M-001",
        "--detail-ref", str(target),
        "--dedupe-key", instance["dedupe_key"],
    ]
    subprocess.run(cmd, cwd=str(DIE), env=clean_env(), capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=30)
    print(f"INGESTED {receipt_id} -> {target}")
    return 0


def cmd_list(_args) -> int:
    if not RECEIPTS.is_dir():
        print("(no receipts stored)")
        return 0
    for path in sorted(RECEIPTS.glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            print(f"{row.get('receipt_id')} | {row.get('platform')} | "
                  f"{row.get('asset_id')} | {row.get('outcome')} | "
                  f"{row.get('reason_code')} | {row.get('evidence_label')}")
        except (OSError, json.JSONDecodeError):
            print(f"{path.name} | UNREADABLE")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--file", required=True)
    p_ingest.set_defaults(func=cmd_ingest)
    p_list = sub.add_parser("list")
    p_list.set_defaults(func=cmd_list)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
