"""Run the bounded FA-034 offline acceptance with durable artifacts."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"lib"))
from pattern_engine_acceptance import accept_fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    fixtures = json.loads((ROOT/"fixtures/procedural-pattern/fixtures.v1.json").read_text())["fixtures"]
    results = [{"fixture": row["name"], "acceptance": accept_fixture(row["request"], output_dir=args.output_dir/row["name"])}
               for row in fixtures]
    passed = all(row["acceptance"]["result"] == "PASS" for row in results)
    print(json.dumps({"task_id": "FA-034", "result": "PASS" if passed else "FAIL", "fixtures": results}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
