# config.py — path, ambang, batas ukuran. Tidak ada rahasia di file ini.
# Ambang operasional dari B4.1 D1-D6 (ASSUMPTION sampai ada data).
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

# B4.1 D5 — wake budget
WAKE_PER_DAY = 4
WAKE_MIN_GAP_MIN = 90

# B4.1 D1 — ambang heartbeat card (menit)
HB_THRESHOLD_MIN = 15          # lantai: max(3x interval harapan, 15 mnt)
HB_SHORT_JOB_MIN = 20          # job <= 20 mnt -> ambang 15 mnt
HB_LONG_JOB_MIN = 60           # job >= 60 mnt -> ambang 30 mnt
HB_LONG_THRESHOLD_MIN = 30

# B4.1 D2 — ambang staleness lane kognitif (jam)
LANE_STALE_WARN_H = 26
LANE_STALE_ALARM_H = 50
LANE_STALE_DEGRADE_H = 72

# B4.1 D4 — batas budget mandiri (USD)
A0_DAILY_USD = 0.0
A0_MISSION_USD = 0.0
A1_DAILY_USD = 5.0
A1_MISSION_USD = 20.0

# B4.1 D6 — retry job
RETRY_MAX = 2
RETRY_BACKOFF_MIN = (2, 8)

# ===== P1: Hermes sources (hard-coded path; JANGAN andalkan HERMES_HOME env) =====
HERMES_HOME = pathlib.Path(r"C:\Users\aethers\AppData\Local\hermes")
HERMES_BIN = HERMES_HOME / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"
KANBAN_DB = HERMES_HOME / "kanban.db"
STATE_DB_DEFAULT = HERMES_HOME / "state.db"
STATE_DB_PROFILE = HERMES_HOME / "profiles" / "income-operator" / "state.db"
CONFIG_YAML = HERMES_HOME / "config.yaml"
CAPABILITIES_FILE = STATE / "CAPABILITIES.jsonl"

# CLI allowlist — argv tetap (tidak pernah dibentuk dari input pemanggil)
CLI_CMDS = {
    "kanban": [str(HERMES_BIN), "kanban", "list", "--json"],
    "cron": [str(HERMES_BIN), "cron", "list"],
    "gateway": [str(HERMES_BIN), "gateway", "status"],
    "sessions": [str(HERMES_BIN), "sessions", "list"],
}
CLI_TIMEOUT = 20

# P1: akses
ACCESS_LOG = PROJ / "ACCESS.jsonl"
RATE_LIMIT = 60
RATE_WINDOW_S = 3600
MAX_TURNS = 20
MAX_SESSION_KB = 12 * 1024
SNIPPET_MAX = 300
EVENTS_VERIFIED = True  # schema EVENTS.jsonl di-record di SCHEMA_NOTES.md
DEFAULT_CAPABILITIES = [
    "kanban", "cron", "gateway", "sessions", "search",
    "briefing", "redact", "economics", "evidence", "wake",
]
