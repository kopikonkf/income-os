from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "company/factory-asset/lib/blueprint_compiler.py"
spec = importlib.util.spec_from_file_location("factory_asset_blueprint_compiler", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

parser = argparse.ArgumentParser()
parser.add_argument("blueprint", type=Path)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
blueprint = json.loads(args.blueprint.read_text(encoding="utf-8-sig"))
plan = mod.compile_blueprint(blueprint)
encoded = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
else:
    print(encoded, end="")