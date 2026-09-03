import argparse
import json
from pathlib import Path

import pytest

from bin import die_engineering_lease as lease


def _args(root: Path, state: Path, owner: str = "runner-a", task_id: str = "FA-001"):
    return argparse.Namespace(
        lease_root=str(root),
        scope="factory-asset",
        task_id=task_id,
        owner=owner,
        state_file=str(state),
        ttl_seconds=600,
    )


def test_pair_acquire_blocks_second_owner_and_release_restores_free(tmp_path):
    root = tmp_path / "leases"
    state_a = tmp_path / "a.json"
    state_b = tmp_path / "b.json"

    acquired = lease.acquire_pair(_args(root, state_a))
    assert acquired["status"] == "ACQUIRED"
    assert acquired["resources"] == ["income-os.repo-write", "factory-asset.FA-001"]
    assert lease.inspect_one(root, "income-os.repo-write")["status"] == "ACTIVE"

    with pytest.raises(lease.LeaseBusy):
        lease.acquire_pair(_args(root, state_b, owner="runner-b", task_id="FA-003"))

    released = lease.release_pair(argparse.Namespace(state_file=str(state_a)))
    assert released["status"] == "RELEASED"
    assert lease.inspect_one(root, "income-os.repo-write")["status"] == "FREE"
    assert not state_a.exists()


def test_expired_record_is_reclaimed_under_guard(tmp_path, monkeypatch):
    root = tmp_path / "leases"
    root.mkdir()
    path = root / "income-os.repo-write.lease.json"
    path.write_text(
        json.dumps(
            {
                "schema": lease.SCHEMA,
                "resource": "income-os.repo-write",
                "token": "old-token",
                "owner": "crashed-runner",
                "task_id": "FA-001",
                "acquired_at": "2026-09-03T00:00:00Z",
                "expires_at": "2026-09-03T00:10:00Z",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        lease,
        "_utc_now",
        lambda: lease.dt.datetime(2026, 9, 3, 1, 0, 0, tzinfo=lease.dt.timezone.utc),
    )
    record = lease.acquire_one(
        root,
        "income-os.repo-write",
        owner="runner-new",
        task_id="FA-003",
        ttl_seconds=600,
        token="new-token",
    )
    assert record["token"] == "new-token"
    assert record["reclaimed_expired_lease"]["token"] == "old-token"


def test_release_requires_matching_token(tmp_path):
    root = tmp_path / "leases"
    lease.acquire_one(
        root,
        "income-os.repo-write",
        owner="runner-a",
        task_id="FA-001",
        ttl_seconds=600,
        token="token-a",
    )
    with pytest.raises(lease.LeaseError, match="LEASE_TOKEN_MISMATCH"):
        lease.release_one(root, "income-os.repo-write", token="token-b")
    assert lease.inspect_one(root, "income-os.repo-write")["status"] == "ACTIVE"


def test_corrupt_active_record_fails_closed(tmp_path):
    root = tmp_path / "leases"
    root.mkdir()
    (root / "income-os.repo-write.lease.json").write_text("not-json", encoding="utf-8")
    with pytest.raises(lease.LeaseError, match="invalid lease record"):
        lease.acquire_one(
            root,
            "income-os.repo-write",
            owner="runner-a",
            task_id="FA-001",
            ttl_seconds=600,
            token="token-a",
        )


def test_resource_names_are_sanitized():
    assert lease._resource_filename("income-os:repo-write") == "income-os_repo-write"
    assert lease._resource_filename("factory-asset.FA-001") == "factory-asset.FA-001"
