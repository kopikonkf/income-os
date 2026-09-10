#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "company/factory-asset/lib"))
from production_prompt_compiler import compile_from_files  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile typed Factory visual requirements into a deterministic provider prompt")
    ap.add_argument("--subject", type=Path, required=True)
    ap.add_argument("--semantic-asset-id", required=True)
    ap.add_argument("--preset-id", required=True)
    ap.add_argument("--preset-revision")
    ap.add_argument("--background-mode", choices=["TRANSPARENT", "PURE_WHITE", "SOLID_NEUTRAL"])
    ap.add_argument("--viewpoint", choices=["SUBJECT_APPROPRIATE", "FRONT", "THREE_QUARTER", "TOP_DOWN", "SIDE", "ISOMETRIC", "CUSTOM"])
    ap.add_argument("--view-instruction")
    ap.add_argument("--visual-out", type=Path, required=True)
    ap.add_argument("--compiled-out", type=Path, required=True)
    args = ap.parse_args()
    overrides = {}
    if args.background_mode: overrides["background_mode"] = args.background_mode
    if args.viewpoint: overrides["viewpoint"] = args.viewpoint
    if args.view_instruction: overrides["view_instruction"] = args.view_instruction
    visual, compiled = compile_from_files(subject_path=args.subject, semantic_asset_id=args.semantic_asset_id, preset_id=args.preset_id, preset_revision=args.preset_revision, overrides=overrides)
    for path, value in [(args.visual_out, visual), (args.compiled_out, compiled)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "visual_spec_sha256": compiled["visual_spec_sha256"], "provider_prompt_sha256": compiled["provider_prompt_sha256"], "compiled_contract_sha256": compiled["compiled_contract_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
