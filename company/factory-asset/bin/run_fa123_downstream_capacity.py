#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
LIB = BASE / 'lib'
sys.path.insert(0, str(LIB))

from fa123_capacity_model import run_fa123_capacity_model


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.tmp-{os.getpid()}')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser(description='Run FA-123 deterministic downstream-capacity model for 100 masters/day.')
    ap.add_argument('--contract', type=Path, default=BASE / 'contracts/fa123-downstream-capacity.v1.json')
    ap.add_argument('--fa122', type=Path, default=BASE / 'receipts/FA-122-20-50-masters-day.receipt.json')
    ap.add_argument('--fa120', type=Path, default=BASE / 'receipts/FA-120-synthetic-throughput-backpressure.receipt.json')
    ap.add_argument('--fa137', type=Path, default=BASE / 'receipts/FA-137-metadata-package-readiness.receipt.json')
    ap.add_argument('--fa205', type=Path, default=BASE / 'receipts/FA-205-founder-qc.receipt.json')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    result = run_fa123_capacity_model(
        contract_path=args.contract,
        fa122_receipt_path=args.fa122,
        fa120_receipt_path=args.fa120,
        fa137_receipt_path=args.fa137,
        fa205_receipt_path=args.fa205,
    )
    if args.output:
        atomic_json(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get('result') == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
