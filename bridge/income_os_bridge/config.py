# config.py — path, ambang, batas ukuran. Tidak ada rahasia di file ini.
# Ambang operasional dari B4.1 D1-D6 (ASSUMPTION sampai ada data).
import ntpath
import os
import pathlib
import posixpath
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class DiePathRoots:
    die_home: str
    die_state_root: str
    muxia_root: str
    die_config_root: str
    die_install_root: str


def _platform_family(platform_name: str | None = None) -> str:
    value = (platform_name or ("windows" if os.name == "nt" else "linux")).strip().lower()
    aliases = {
        "nt": "windows",
        "win32": "windows",
        "windows": "windows",
        "posix": "linux",
        "linux": "linux",
    }
    if value not in aliases:
        raise ValueError(f"unsupported DIE path platform: {value}")
    return aliases[value]


def resolve_die_path_roots(
    env: Mapping[str, str] | None = None,
    *,
    platform_name: str | None = None,
) -> DiePathRoots:
    supplied = os.environ if env is None else env
    platform = _platform_family(platform_name)
    path_api = ntpath if platform == "windows" else posixpath

    if platform == "windows":
        die_home_default = r"C:\DIE"
        state_root_default = None
        config_root_default = path_api.join(supplied.get("PROGRAMDATA", r"C:\ProgramData"), "DIE")
        install_root_default = path_api.join(supplied.get("ProgramFiles", r"C:\Program Files"), "DIE")
    else:
        die_home_default = "/srv/die"
        state_root_default = "/var/lib/die"
        config_root_default = "/etc/die"
        install_root_default = "/opt/die"

    def absolute(name: str, value: str) -> str:
        text = str(value).strip()
        if not text or not path_api.isabs(text):
            raise ValueError(f"{name} must be an absolute path")
        return path_api.normpath(text)

    die_home = absolute("DIE_HOME", supplied.get("DIE_HOME", die_home_default))
    state_root = absolute("DIE_STATE_ROOT", supplied.get("DIE_STATE_ROOT", state_root_default or die_home))
    muxia_default = path_api.join(state_root, "muxia") if platform == "windows" else "/var/lib/muxia"
    muxia_root = absolute("MUXIA_ROOT", supplied.get("MUXIA_ROOT", muxia_default))
    config_root = absolute("DIE_CONFIG_ROOT", supplied.get("DIE_CONFIG_ROOT", config_root_default))
    install_root = absolute("DIE_INSTALL_ROOT", supplied.get("DIE_INSTALL_ROOT", install_root_default))
    return DiePathRoots(
        die_home=die_home,
        die_state_root=state_root,
        muxia_root=muxia_root,
        die_config_root=config_root,
        die_install_root=install_root,
    )


_PATH_ROOTS = resolve_die_path_roots()
DIE_HOME = pathlib.Path(_PATH_ROOTS.die_home)
DIE_STATE_ROOT = pathlib.Path(_PATH_ROOTS.die_state_root)
MUXIA_ROOT = pathlib.Path(_PATH_ROOTS.muxia_root)
DIE_CONFIG_ROOT = pathlib.Path(_PATH_ROOTS.die_config_root)
DIE_INSTALL_ROOT = pathlib.Path(_PATH_ROOTS.die_install_root)
STATE = DIE_STATE_ROOT / "state"
WORKSPACES = DIE_STATE_ROOT / "workspaces"
IDENTITY_REGISTRY = DIE_HOME / "company" / "identity-registry.json"
HERMES_PROFILE = "income-operator"
OPERATIONAL_CONTROL_PLANE = f"hermes-operator/{HERMES_PROFILE}"
CANONICAL_WRITER = "die-state-manager"
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

# P5 v1 — bounded semantic context
CONTEXT_SNAPSHOT_TTL_S = 15 * 60
CONTEXT_EVENT_LIMIT = 20
STATE_REQUEST_MAX_BYTES = 64 * 1024
STATE_OBJECT_MAX_BYTES = 8 * 1024
CANON_MANIFEST_MAX_BYTES = 24 * 1024
CANON_CONTEXT_MAX_BYTES = 16 * 1024

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

# ===== P1: Hermes sources =====
# DIE-202 migrates the Hermes runtime itself. This hook removes the drive
# dependency now while preserving the current Windows default.
if os.environ.get("DIE_HERMES_HOME"):
    HERMES_HOME = pathlib.Path(os.environ["DIE_HERMES_HOME"])
elif os.name == "nt":
    HERMES_HOME = pathlib.Path(r"C:\Users\aethers\AppData\Local\hermes")
else:
    HERMES_HOME = DIE_STATE_ROOT / "hermes"

if os.environ.get("DIE_HERMES_EXE"):
    HERMES_BIN = pathlib.Path(os.environ["DIE_HERMES_EXE"])
elif os.name == "nt":
    HERMES_BIN = HERMES_HOME / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"
else:
    HERMES_BIN = HERMES_HOME / "bin" / "hermes"
KANBAN_DB = HERMES_HOME / "kanban.db"
STATE_DB_DEFAULT = HERMES_HOME / "state.db"
STATE_DB_PROFILE = HERMES_HOME / "profiles" / HERMES_PROFILE / "state.db"
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
