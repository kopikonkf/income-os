#!/usr/bin/env python3
"""Cross-session engineering lease helper for the Windows Architect MCP control plane.

The helper coordinates repository writers through a shared filesystem root using
OS-released guard locks plus TTL-bounded JSON lease records. It never reads or
stores credentials and never touches the live DIE or OAUTH trees.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import socket
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Iterator

SCHEMA = "die.engineering-lease.v1"
DEFAULT_TTL_SECONDS = 5400
MIN_TTL_SECONDS = 300
MAX_TTL_SECONDS = 7200


class LeaseError(RuntimeError):
    pass


class LeaseBusy(LeaseError):
    pass


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise LeaseError("lease timestamp must be timezone-aware")
    return parsed.astimezone(dt.timezone.utc)


def _resource_filename(resource: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    name = "".join(ch if ch in allowed else "_" for ch in resource)
    if not name or name in {".", ".."}:
        raise LeaseError("invalid lease resource")
    return name


@contextlib.contextmanager
def _guard(lock_root: Path, resource: str) -> Iterator[None]:
    """Serialize changes to one lease record.

    Guard locks are kernel-held and released automatically if the process exits.
    The persistent guard file itself carries no ownership semantics.
    """
    lock_root.mkdir(parents=True, exist_ok=True)
    guard_path = lock_root / f".{_resource_filename(resource)}.guard"
    with guard_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_record(path: Path) -> dict:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # fail closed on corrupt lock state
        raise LeaseError(f"invalid lease record: {path}") from exc
    required = {"schema", "resource", "token", "owner", "acquired_at", "expires_at"}
    if record.get("schema") != SCHEMA or not required.issubset(record):
        raise LeaseError(f"invalid lease record contract: {path}")
    return record


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)


def acquire_one(lock_root: Path, resource: str, *, owner: str, task_id: str, ttl_seconds: int, token: str) -> dict:
    now = _utc_now()
    expires = now + dt.timedelta(seconds=ttl_seconds)
    path = lock_root / f"{_resource_filename(resource)}.lease.json"
    with _guard(lock_root, resource):
        reclaimed = None
        if path.exists():
            existing = _read_record(path)
            existing_expiry = _parse_iso(existing["expires_at"])
            if existing_expiry > now:
                raise LeaseBusy(
                    f"LEASE_BUSY resource={resource} owner={existing['owner']} "
                    f"task_id={existing.get('task_id','')} expires_at={existing['expires_at']}"
                )
            reclaimed = {
                "token": existing["token"],
                "owner": existing["owner"],
                "task_id": existing.get("task_id"),
                "expired_at": existing["expires_at"],
            }
        record = {
            "schema": SCHEMA,
            "resource": resource,
            "token": token,
            "owner": owner,
            "task_id": task_id,
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "acquired_at": _iso(now),
            "expires_at": _iso(expires),
            "ttl_seconds": ttl_seconds,
            "reclaimed_expired_lease": reclaimed,
        }
        _write_json_atomic(path, record)
        return record


def release_one(lock_root: Path, resource: str, *, token: str) -> dict:
    path = lock_root / f"{_resource_filename(resource)}.lease.json"
    with _guard(lock_root, resource):
        if not path.exists():
            return {"resource": resource, "status": "ALREADY_RELEASED"}
        existing = _read_record(path)
        if existing["token"] != token:
            raise LeaseError(f"LEASE_TOKEN_MISMATCH resource={resource}")
        path.unlink()
        return {"resource": resource, "status": "RELEASED"}


def inspect_one(lock_root: Path, resource: str) -> dict:
    path = lock_root / f"{_resource_filename(resource)}.lease.json"
    with _guard(lock_root, resource):
        if not path.exists():
            return {"schema": SCHEMA, "resource": resource, "status": "FREE"}
        record = _read_record(path)
        status = "ACTIVE" if _parse_iso(record["expires_at"]) > _utc_now() else "EXPIRED"
        return {
            "schema": SCHEMA,
            "resource": resource,
            "status": status,
            "owner": record["owner"],
            "task_id": record.get("task_id"),
            "acquired_at": record["acquired_at"],
            "expires_at": record["expires_at"],
        }


def acquire_pair(args: argparse.Namespace) -> dict:
    if not (MIN_TTL_SECONDS <= args.ttl_seconds <= MAX_TTL_SECONDS):
        raise LeaseError(f"ttl_seconds must be within {MIN_TTL_SECONDS}..{MAX_TTL_SECONDS}")
    lock_root = Path(args.lease_root).resolve()
    state_file = Path(args.state_file).resolve()
    if state_file.exists():
        raise LeaseError(f"state file already exists: {state_file}")
    token = uuid.uuid4().hex
    resources = ["income-os.repo-write", f"{args.scope}.{args.task_id}"]
    acquired: list[dict] = []
    try:
        for resource in resources:
            acquired.append(
                acquire_one(
                    lock_root,
                    resource,
                    owner=args.owner,
                    task_id=args.task_id,
                    ttl_seconds=args.ttl_seconds,
                    token=token,
                )
            )
    except Exception:
        for record in reversed(acquired):
            with contextlib.suppress(Exception):
                release_one(lock_root, record["resource"], token=token)
        raise
    state = {
        "schema": SCHEMA,
        "lease_root": str(lock_root),
        "state_file": str(state_file),
        "token": token,
        "owner": args.owner,
        "task_id": args.task_id,
        "resources": [record["resource"] for record in acquired],
        "expires_at": min(record["expires_at"] for record in acquired),
    }
    _write_json_atomic(state_file, state)
    return {**state, "status": "ACQUIRED"}


def release_pair(args: argparse.Namespace) -> dict:
    state_file = Path(args.state_file).resolve()
    state = json.loads(state_file.read_text(encoding='utf-8'))
    if state.get("schema") != SCHEMA or not state.get("token") or not state.get("resources"):
        raise LeaseError(f"invalid pair state file: {state_file}")
    lock_root = Path(state["lease_root"])
    results = []
    errors = []
    for resource in reversed(state["resources"]):
        try:
            results.append(release_one(lock_root, resource, token=state["token"]))
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        raise LeaseError("; ".join(errors))
    state_file.unlink(missing_ok=True)
    return {"schema": SCHEMA, "status": "RELEASED", "results": results}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DIE engineering lease helper")
    sub = parser.add_subparsers(dest="command", required=True)

    acquire = sub.add_parser("acquire-pair")
    acquire.add_argument("--lease-root", required=True)
    acquire.add_argument("--scope", required=True)
    acquire.add_argument("--task-id", required=True)
    acquire.add_argument("--owner", required=True)
    acquire.add_argument("--state-file", required=True)
    acquire.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)

    release = sub.add_parser("release-pair")
    release.add_argument("--state-file", required=True)

    inspect = sub.add_parser("inspect")
    inspect.add_argument("--lease-root", required=True)
    inspect.add_argument("--resource", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "acquire-pair":
            result = acquire_pair(args)
        elif args.command == "release-pair":
            result = release_pair(args)
        elif args.command == "inspect":
            result = inspect_one(Path(args.lease_root).resolve(), args.resource)
        else:  # pragma: no cover
            raise LeaseError("unsupported command")
    except LeaseBusy as exc:
        print(json.dumps({"schema": SCHEMA, "status": "BUSY", "error": str(exc)}, sort_keys=True))
        return 3
    except Exception as exc:
        print(json.dumps({"schema": SCHEMA, "status": "ERROR", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
