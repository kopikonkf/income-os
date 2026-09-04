from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FACTORY_ROOT = REPO_ROOT / "company/factory-asset"


def sync_console_mirror(dest: Path) -> None:
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    console_src = FACTORY_ROOT / "console-prototype"
    console_dst = dest / "console-prototype"
    if console_dst.exists():
        shutil.rmtree(console_dst)
    shutil.copytree(console_src, console_dst)
    support_root = dest / "company/factory-asset"
    for name in ("lib", "schemas", "registries", "fixtures"):
        src = FACTORY_ROOT / name
        dst = support_root / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", required=True)
    args = parser.parse_args()
    sync_console_mirror(Path(args.dest))


if __name__ == "__main__":
    main()
