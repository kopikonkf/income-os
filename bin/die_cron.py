"""Deterministic DIE cron runners.

B1.7/B2 constraints:
- no LLM, no network, stdlib only
- no Hermes SQLite access; Kanban is queried through the CLI boundary
- EVENTS/DECISIONS/ECONOMICS are written only through die_event.py
- briefing writes only state/projection through income_os_bridge
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
from collections import Counter

DIE = pathlib.Path(os.environ.get("DIE_HOME", r"C:\DIE"))
BIN = DIE / "bin"
STATE = DIE / "state"
BRIDGE = DIE / "bridge"
PROJECTION = STATE / "projection"
ORGANISM = STATE / "organism-test"
HERMES_AGENT_ROOT = pathlib.Path(r"C:\Users\aethers\AppData\Local\hermes")
PYTHON = pathlib.Path(sys.executable)

HB_SHORT_MIN = 15
HB_LONG_MIN = 30
HB_LONG_JOB_MIN = 60
WAKE_CLASSES = {"CRITICAL", "STRATEGIC"}


def clean_env():
    env = os.environ.copy()
    for key in list(env):
        if any(x in key.upper() for x in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")):
            env.pop(key, None)
    return env


def run(cmd, cwd=DIE, timeout=30):
    return subprocess.run(cmd, cwd=str(cwd), env=clean_env(), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout)


def resolve_hermes_executable(env=None, python_executable=None, which=None):
    env = os.environ if env is None else env
    python_executable = sys.executable if python_executable is None else python_executable
    which = shutil.which if which is None else which
    candidates = []
    if env.get("DIE_HERMES_EXE"):
        candidates.append(pathlib.Path(env["DIE_HERMES_EXE"]))
    for name in ("hermes.exe", "hermes"):
        resolved = which(name)
        if resolved:
            candidates.append(pathlib.Path(resolved))
    candidates.extend([
        pathlib.Path(python_executable).with_name("hermes.exe"),
        HERMES_AGENT_ROOT / "hermes-agent" / "venv" / "Scripts" / "hermes.exe",
        HERMES_AGENT_ROOT / "bin" / "hermes.exe",
    ])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    attempted = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(
        f"Hermes executable tidak ditemukan; set DIE_HERMES_EXE. tried: {attempted}"
    )


def hermes(*args, timeout=30):
    return run([str(resolve_hermes_executable()), *args], timeout=timeout)


def emit(
    cls,
    summary,
    detail=None,
    *,
    dedupe_key=None,
    alarm_state=None,
    resolves_event_id=None,
):
    cmd = [str(PYTHON), str(BIN / "die_event.py"), "event", "--class", cls,
           "--source", "cron", "--summary", summary[:140]]
    if detail:
        cmd += ["--detail-ref", str(detail)]
    if dedupe_key:
        cmd += ["--dedupe-key", dedupe_key]
    if alarm_state:
        cmd += ["--alarm-state", alarm_state]
    if resolves_event_id:
        cmd += ["--resolves-event-id", resolves_event_id]
    result = run(cmd, timeout=20)
    if result.returncode:
        print(f"die_event failed: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def parse_time(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value, dt.timezone.utc)
    text = str(value).strip()
    try:
        if text.isdigit():
            return dt.datetime.fromtimestamp(int(text), dt.timezone.utc)
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except ValueError:
        return None


def json_rows(stdout):
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("tasks", "cards", "items", "data"):
            if isinstance(value.get(key), list):
                return value[key]
    return None


def kanban_rows():
    result = hermes("kanban", "list", "--json", timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "hermes kanban list failed")
    rows = json_rows(result.stdout)
    if rows is None:
        raise RuntimeError("kanban CLI returned non-JSON or unknown JSON shape")
    return rows


def task_id(row):
    return row.get("id") or row.get("task_id") or row.get("card_id")


def heartbeat(row):
    return parse_time(row.get("last_heartbeat_at") or row.get("heartbeat_at") or
                      row.get("last_heartbeat") or row.get("created_at"))


def threshold(row):
    seconds = row.get("max_runtime_seconds") or row.get("time_budget_seconds")
    if seconds is None and row.get("time_budget_min") is not None:
        seconds = float(row["time_budget_min"]) * 60
    if seconds is not None and float(seconds) / 60 >= HB_LONG_JOB_MIN:
        return HB_LONG_MIN
    return HB_SHORT_MIN


def active(row):
    return str(row.get("status", "")).lower() in {"running", "in_progress", "active"}


def heartbeat_run():
    try:
        rows = kanban_rows()
    except Exception as exc:
        emit(
            "CRITICAL",
            f"die-heartbeat gagal membaca Kanban CLI: {exc}",
            dedupe_key="health:die-heartbeat:kanban-cli",
            alarm_state="open",
        )
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    now = dt.datetime.now(dt.timezone.utc)
    stale = []
    for row in rows:
        if not active(row):
            continue
        ident = task_id(row)
        hb = heartbeat(row)
        if not ident or hb is None:
            continue
        age = (now - hb).total_seconds() / 60
        if age > threshold(row):
            stale.append((ident, age, row))
    blocked = 0
    for ident, age, _row in stale:
        reason = f"heartbeat basi {age:.0f}m"
        result = hermes("kanban", "block", str(ident), "heartbeat", "stale", "-", reason,
                        "--kind", "transient", timeout=20)
        if result.returncode:
            emit("CRITICAL", f"die-heartbeat gagal memblokir {ident}: {result.stderr.strip()}")
            print(result.stderr.strip(), file=sys.stderr)
            return 1
        blocked += 1
        emit("WARNING", f"card {ident} blocked: {reason}")
    summary = f"heartbeat-cron: {sum(1 for r in rows if active(r))} active cards, {blocked} blocked"
    if not emit(
        "INFO",
        summary,
        dedupe_key="health:die-heartbeat:kanban-cli",
        alarm_state="resolved",
    ):
        return 1
    print(summary)
    return 0


def briefing_run():
    result = run([str(PYTHON), "-m", "income_os_bridge", "briefing", "--out", str(PROJECTION)], cwd=BRIDGE, timeout=60)
    if result.returncode:
        emit("CRITICAL", f"die-briefing gagal: {result.stderr.strip() or result.stdout.strip()}")
        print(result.stderr or result.stdout, file=sys.stderr)
        return 1
    ORGANISM.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    truth = hermes("kanban", "list", timeout=20)
    truth_path = ORGANISM / f"groundtruth-{stamp}.txt"
    truth_path.write_text(truth.stdout if truth.stdout else truth.stderr, encoding="utf-8")
    if truth.returncode:
        emit("CRITICAL", "die-briefing gagal menyimpan ground truth Kanban", truth_path)
        return 1
    emit("INFO", "die-briefing: BRIEFING.md dan ground truth ditulis", truth_path)
    print(result.stdout.strip() or "briefing complete")
    return 0


def read_events():
    path = STATE / "EVENTS.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def summary_run():
    now = dt.datetime.now(dt.timezone.utc)
    events = read_events()
    recent = []
    for event in events:
        stamp = parse_time(event.get("ts"))
        if stamp and (now - stamp).total_seconds() <= 86400:
            recent.append(event)
    counts = Counter(e.get("class", "UNKNOWN") for e in recent)
    alarms = [e for e in recent if e.get("class") in {"CRITICAL", "WARNING"}]
    economics = STATE / "ECONOMICS.jsonl"
    econ_lines = [x for x in economics.read_text(encoding="utf-8").splitlines() if x.strip()] if economics.exists() else []
    print("# DIE DAILY SUMMARY")
    print(f"as_of: {now.isoformat(timespec='seconds').replace('+00:00', 'Z')}")
    print(f"events_24h: {len(recent)} | by_class: {dict(counts)}")
    print("alarms:")
    for e in alarms[-10:]:
        print(f"- {e.get('class')} {e.get('event_id')}: {e.get('summary', '')}")
    if not alarms:
        print("- none")
    if econ_lines:
        print(f"economics_rows: {len(econ_lines)} (inspect state/ECONOMICS.jsonl for verified status)")
    else:
        print("economics: belum ada baris ECONOMICS.jsonl (bukan USD 0.00)")
    if not emit("INFO", f"die-summary: {len(recent)} event 24j, {len(alarms)} alarm"):
        return 1
    return 0


def audit_run():
    findings = []
    for path in (DIE / "workspaces").glob("*/RESULT.json"):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if result.get("status") == "done" and not result.get("evidence"):
            findings.append(f"done tanpa evidence: {path.parent.name}")
    try:
        rows = kanban_rows()
        for row in rows:
            if active(row) and heartbeat(row) is None:
                findings.append(f"active card tanpa heartbeat: {task_id(row)}")
    except Exception as exc:
        findings.append(f"Kanban audit tidak tersedia: {exc}")
    if findings:
        for item in findings:
            if not emit("WARNING", f"die-audit: {item}"):
                return 1
    else:
        if not emit("INFO", "die-audit: tidak ada temuan mekanis"):
            return 1
    print("# DIE AUDIT")
    print("findings:")
    print("- none" if not findings else "\n".join(f"- {x}" for x in findings))
    return 0


def main(mode):
    return {"heartbeat": heartbeat_run, "briefing": briefing_run,
            "summary": summary_run, "audit": audit_run}[mode]()

if __name__ == "__main__":
    name = pathlib.Path(sys.argv[0]).stem
    mode = name.removeprefix("die_")
    raise SystemExit(main(mode))
