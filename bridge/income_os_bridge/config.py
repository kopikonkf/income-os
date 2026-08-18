# config.py — path, ambang, batas ukuran. Tidak ada rahasia di file ini.
import os, pathlib

DIE_HOME = pathlib.Path(os.environ.get("DIE_HOME", r"C:\DIE"))
STATE = DIE_HOME / "state"
EVENTS = STATE / "EVENTS.jsonl"
PROJ = STATE / "projection"
PROJ_EVENTS = PROJ / "EVENTS.jsonl"
BRIEFING = PROJ / "BRIEFING.md"
CURSOR = PROJ / ".cursor"
WAKE_FLAG = PROJ / "WAKE.flag"

CLASSES = ("INFO", "NOTICE", "WARNING", "CRITICAL", "STRATEGIC")
WAKE_CLASSES = ("CRITICAL", "STRATEGIC")
CLASS_ORDER = {c: i for i, c in enumerate(CLASSES)}

PAGE_DEFAULT = 50
PAGE_MAX = 200
MAX_RESP_BYTES = 32 * 1024
MAX_BRIEF_BYTES = 8 * 1024
WAKE_PER_DAY = 4
WAKE_MIN_GAP_MIN = 90
