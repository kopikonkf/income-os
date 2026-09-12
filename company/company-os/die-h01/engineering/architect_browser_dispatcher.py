from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

CONTRACT = "die.h01.architect-browser-dispatcher.v1"
TERMINAL = {"DONE", "BLOCKED", "VERIFYING"}


class DispatchError(RuntimeError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code


@dataclass(frozen=True)
class DispatchRequest:
    project_name: str
    task_id: str
    principal_id: str
    lease_token: str
    dispatch_id: str

    @property
    def marker(self) -> str:
        return f"MC005_ARCHITECT_RESULT_{self.dispatch_id}"


@dataclass(frozen=True)
class BrowserBinding:
    resource_id: str
    browser_executable: str
    user_data_dir: str
    profile_directory: str
    node_executable: str
    cdp_driver: str
    lease_root: str


def build_bootstrap(req: DispatchRequest) -> str:
    if not all((req.project_name, req.task_id, req.principal_id, req.lease_token, req.dispatch_id)):
        raise DispatchError("E_BOOTSTRAP_FIELDS")
    return (
        "MISSION CONTROL - ARCHITECT NATIVE MCP BOOTSTRAP\n"
        f"task_id={req.task_id}\n"
        f"mission_principal_id={req.principal_id}\n"
        f"mission_lease_token={req.lease_token}\n"
        f"FIRST: recover relevant cross-session context from the ChatGPT Project \"{req.project_name}\". "
        "Consult project context and prior sessions before task execution; then reconcile that context with current canon.\n"
        "For execution, use ChatGPT Architect MCP and Universal MCP. Do not simulate tool calls or substitute unsupported execution paths.\n"
        "THEN call mission.task.get through Universal MCP to fetch the complete current Work Card and constraints before execution.\n"
        "Do not rely on this bootstrap for task details and do not simulate Mission Protocol calls.\n"
        "Use mission.task.checkpoint / mission.task.complete / mission.task.block for durable state.\n"
        f"After durable completion succeeds, put this exact marker on the final line: {req.marker}"
    )


class ProfileLease:
    """Atomic host-local lease; contains coordination metadata only, never Mission secrets."""

    def __init__(self, root: str | Path, resource_id: str, *, ttl_seconds: int = 1800):
        self.root = Path(root)
        self.resource_id = resource_id
        self.ttl_seconds = ttl_seconds
        self.lock_dir = self.root / f"{resource_id}.lock"
        self.lease_id: str | None = None

    def acquire(self, *, task_id: str, dispatch_id: str, principal_id: str) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        now = time.time()
        try:
            self.lock_dir.mkdir()
        except FileExistsError:
            state = self._read_state()
            expires = float(state.get("expires_epoch", 0)) if state else 0
            if expires > now:
                raise DispatchError("E_PROFILE_BUSY", self.resource_id)
            shutil.rmtree(self.lock_dir, ignore_errors=True)
            try:
                self.lock_dir.mkdir()
            except FileExistsError as exc:
                raise DispatchError("E_PROFILE_BUSY", self.resource_id) from exc
        self.lease_id = uuid.uuid4().hex
        state = {
            "schema": "die.h01.architect-browser-profile-lease.v1",
            "resource_id": self.resource_id,
            "lease_id": self.lease_id,
            "task_id": task_id,
            "dispatch_id": dispatch_id,
            "principal_id": principal_id,
            "acquired_epoch": now,
            "expires_epoch": now + self.ttl_seconds,
            "pid": os.getpid(),
        }
        (self.lock_dir / "lease.json").write_text(json.dumps(state, sort_keys=True) + "\n", encoding="utf-8")
        return state

    def _read_state(self) -> dict[str, Any]:
        try:
            return json.loads((self.lock_dir / "lease.json").read_text(encoding="utf-8"))
        except Exception:
            return {}

    def release(self) -> None:
        if not self.lease_id:
            return
        state = self._read_state()
        if state.get("lease_id") != self.lease_id:
            raise DispatchError("E_PROFILE_LEASE_TOKEN_MISMATCH", self.resource_id)
        shutil.rmtree(self.lock_dir)
        self.lease_id = None


class NodeCdpSession:
    """Starts the dependency-light Node CDP driver and never receives cookies/session bytes."""

    def __init__(self, binding: BrowserBinding, *, startup_timeout: float = 90.0):
        self.binding = binding
        self.startup_timeout = startup_timeout
        self.proc: subprocess.Popen[str] | None = None

    def open_and_submit(self, bootstrap: str) -> dict[str, Any]:
        cmd = [
            self.binding.node_executable,
            self.binding.cdp_driver,
            "--browser-executable", self.binding.browser_executable,
            "--user-data-dir", self.binding.user_data_dir,
            "--profile-directory", self.binding.profile_directory,
        ]
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps({"bootstrap": bootstrap}) + "\n")
        self.proc.stdin.flush()
        line = self._readline_timeout(self.proc.stdout, self.startup_timeout)
        if not line:
            err = self._stderr_tail()
            raise DispatchError("E_CDP_SUBMIT_TIMEOUT", err)
        try:
            status = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DispatchError("E_CDP_STATUS_JSON", line[:500]) from exc
        if status.get("status") != "SUBMITTED":
            raise DispatchError(str(status.get("error") or "E_CDP_SUBMIT"))
        return status

    @staticmethod
    def _readline_timeout(stream: Any, timeout: float) -> str:
        if stream is None:
            return ""
        q: queue.Queue[str] = queue.Queue(maxsize=1)
        threading.Thread(target=lambda: q.put(stream.readline()), daemon=True).start()
        try:
            return q.get(timeout=timeout).strip()
        except queue.Empty:
            return ""

    def _stderr_tail(self) -> str:
        if not self.proc or self.proc.stderr is None:
            return ""
        if self.proc.poll() is None:
            return ""
        return self.proc.stderr.read()[-1000:]

    def close(self) -> bool:
        if not self.proc:
            return True
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=12)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait(timeout=5)
        return self.proc.returncode == 0


def _durable_evidence(task: dict[str, Any], req: DispatchRequest) -> dict[str, Any] | None:
    if task.get("id") != req.task_id or task.get("owner_principal_id") != req.principal_id:
        raise DispatchError("E_MISSION_IDENTITY_MISMATCH")
    status = str(task.get("status") or "")
    checkpoints = task.get("checkpoints") or []
    owned = [c for c in checkpoints if c.get("principal_id") == req.principal_id]
    if status in TERMINAL:
        return {"kind": "TERMINAL", "status": status, "checkpoint_count": len(owned)}
    if owned:
        last = owned[-1]
        return {"kind": "CHECKPOINT", "status": status, "checkpoint_id": last.get("id"), "progress": last.get("progress")}
    return None


def dispatch_canary(
    req: DispatchRequest,
    binding: BrowserBinding,
    mission_get: Callable[[], dict[str, Any]],
    *,
    session_factory: Callable[[BrowserBinding], Any] = NodeCdpSession,
    poll_seconds: float = 1.0,
    observe_timeout: float = 180.0,
) -> dict[str, Any]:
    """H01-301 bounded canary dispatcher. Long-running production use waits for H01-302."""
    lease = ProfileLease(binding.lease_root, binding.resource_id)
    session = None
    opened = submitted = closed = released = False
    evidence = None
    receipt: dict[str, Any] | None = None
    lease.acquire(task_id=req.task_id, dispatch_id=req.dispatch_id, principal_id=req.principal_id)
    try:
        session = session_factory(binding)
        opened = True
        browser_status = session.open_and_submit(build_bootstrap(req))
        submitted = True
        deadline = time.monotonic() + observe_timeout
        while time.monotonic() < deadline:
            raw = mission_get()
            task = raw.get("task", raw)
            evidence = _durable_evidence(task, req)
            if evidence:
                break
            time.sleep(poll_seconds)
        if not evidence:
            raise DispatchError("E_DURABLE_EVIDENCE_TIMEOUT")
        receipt = {
            "schema": CONTRACT,
            "status": "PASS",
            "task_id": req.task_id,
            "principal_id": req.principal_id,
            "dispatch_id": req.dispatch_id,
            "completion_marker": req.marker,
            "browser_resource_id": binding.resource_id,
            "browser_submit": {k: browser_status.get(k) for k in ("status", "browser_pid", "debug_host", "debug_port", "url")},
            "durable_evidence": evidence,
            "canary_only_until": "H01-302",
        }
    finally:
        if session is not None:
            closed = bool(session.close())
        try:
            lease.release(); released = True
        finally:
            if session is not None:
                setattr(session, "dispatcher_finally", {"browser_closed": closed, "profile_lease_released": released, "submitted": submitted, "opened": opened})
            if receipt is not None:
                receipt["browser_closed"] = closed
                receipt["profile_lease_released"] = released
    assert receipt is not None
    return receipt
