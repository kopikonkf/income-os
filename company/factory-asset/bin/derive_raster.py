#!/usr/bin/env python3
"""Local FA-021 conversion CLI; never dispatches providers or publishes."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from raster_derivative import RasterDerivativeError, convert


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", required=True)
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    try:
        recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8-sig"))
        result = convert(args.master, recipe, args.output_root)
    except (RasterDerivativeError, OSError, ValueError) as exc:
        print(json.dumps({"conversion_status": "FAILED", "code": getattr(exc, "code", "INPUT_OR_IO_ERROR"),
                          "message": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    # Exit 0 means conversion completed, not package compatibility or publication.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
