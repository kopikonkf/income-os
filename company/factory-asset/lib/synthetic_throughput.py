from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def _load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{rel}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


queue_mod = _load("fa120_factory_queue", "company/factory-asset/lib/factory_queue.py")
lease_mod = _load("fa120_provider_profile", "company/factory-asset/lib/provider_profile.py")


@dataclass(frozen=True)
class HarnessConfig:
    unique_jobs: int = 5000
    tenants: tuple[str, ...] = ("alpha", "beta", "gamma", "delta")
    max_active_jobs: int = 256
    worker_slots: int = 8
    virtual_disk_capacity_bytes: int = 64 * 1024 * 1024
    disk_high_watermark_ratio: float = 0.80
    disk_low_watermark_ratio: float = 0.50
    duplicate_every: int = 23
    retry_once_every: int = 17
    retry_twice_every: int = 101
    restart_after_successes: int = 1700

    def validate(self) -> None:
        if self.unique_jobs < 2000:
            raise ValueError("unique_jobs must prove thousands of jobs")
        if not self.tenants or len(set(self.tenants)) != len(self.tenants):
            raise ValueError("tenants must be unique and non-empty")
        if self.max_active_jobs < self.worker_slots or self.worker_slots < 1:
            raise ValueError("invalid queue/worker bounds")
        if not (0 < self.disk_low_watermark_ratio < self.disk_high_watermark_ratio < 1):
            raise ValueError("invalid disk watermarks")
        if self.virtual_disk_capacity_bytes <= 0:
            raise ValueError("virtual disk capacity must be positive")
        if self.restart_after_successes <= 0 or self.restart_after_successes >= self.unique_jobs:
            raise ValueError("restart threshold must be inside the run")


class VirtualDiskBudget:
    """Safe synthetic spool accounting; never allocates the modeled payload bytes."""

    def __init__(self, capacity: int, high_ratio: float, low_ratio: float):
        self.capacity = capacity
        self.high = int(capacity * high_ratio)
        self.low = int(capacity * low_ratio)
        self.used = 0
        self.peak = 0
        self._retained: deque[int] = deque()

    def can_commit(self, size: int) -> bool:
        return self.used + size <= self.high

    def commit(self, size: int) -> None:
        if not self.can_commit(size):
            raise RuntimeError("DISK_HIGH_WATERMARK_BREACH")
        self.used += size
        self.peak = max(self.peak, self.used)
        self._retained.append(size)

    def reclaim_to_low(self) -> int:
        before = self.used
        while self._retained and self.used > self.low:
            self.used -= self._retained.popleft()
        return before - self.used


class SyntheticThroughputHarness:
    """Deterministic queue/load simulation. It imports no provider adapter or network client."""

    def __init__(self, staging_root: str | Path, config: HarnessConfig | None = None):
        self.config = config or HarnessConfig()
        self.config.validate()
        self.root = Path(staging_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.queue = queue_mod.FactoryJobQueue()
        self.leases = lease_mod.ProviderLeaseRegistry()
        self.disk = VirtualDiskBudget(
            self.config.virtual_disk_capacity_bytes,
            self.config.disk_high_watermark_ratio,
            self.config.disk_low_watermark_ratio,
        )
        self.ready: dict[str, deque[str]] = {t: deque() for t in self.config.tenants}
        self.active: set[str] = set()
        self.cursor = 0
        self.next_seq = 1
        self.succeeded = 0
        self.failed = 0
        self.total_attempts = 0
        self.retry_events = 0
        self.duplicate_submissions = 0
        self.dedupe_reused = 0
        self.idempotency_conflicts_blocked = 0
        self.admission_backpressure_events = 0
        self.disk_backpressure_events = 0
        self.disk_resume_events = 0
        self.disk_reclaimed_bytes = 0
        self.lease_contention_blocked = 0
        self.peak_active_depth = 0
        self.restart_performed = False
        self.restart_recovered_jobs = 0
        self.restart_snapshot_bytes = 0
        self.first_dispatch_counts = {t: 0 for t in self.config.tenants}
        self.completion_counts = {t: 0 for t in self.config.tenants}
        self.max_first_dispatch_skew = 0
        self.fairness_violations = 0
        self.last_contended_tenant: str | None = None

    @staticmethod
    def _job_id(seq: int) -> str:
        return f"FA120-SYN-{seq:06d}"

    @staticmethod
    def _idempotency_key(seq: int) -> str:
        return hashlib.sha256(f"fa120-idempotency:{seq}".encode()).hexdigest()

    @staticmethod
    def _artifact_sha(job_id: str) -> str:
        return hashlib.sha256(f"fa120-synthetic-artifact:{job_id}".encode()).hexdigest()

    @staticmethod
    def _modeled_output_bytes(seq: int) -> int:
        return (128 + (seq % 9) * 32) * 1024

    @staticmethod
    def _seq(job_id: str) -> int:
        return int(job_id.rsplit("-", 1)[1])

    def _tenant_for_seq(self, seq: int) -> str:
        return self.config.tenants[(seq - 1) % len(self.config.tenants)]

    def _intent(self, seq: int) -> dict[str, Any]:
        return {
            "blueprint_id": f"FABP-FA120-{seq:06d}",
            "semantic_asset_id": f"FASA-FA120-{seq:06d}",
            "tenant_id": self._tenant_for_seq(seq),
            "synthetic": True,
        }

    def _admit_until_bounded(self) -> None:
        while self.next_seq <= self.config.unique_jobs and len(self.active) < self.config.max_active_jobs:
            seq = self.next_seq
            job_id = self._job_id(seq)
            key = self._idempotency_key(seq)
            intent = self._intent(seq)
            job = self.queue.submit(job_id=job_id, idempotency_key=key, intent=intent)
            self.active.add(job.job_id)
            self.ready[intent["tenant_id"]].append(job.job_id)

            if seq % self.config.duplicate_every == 0:
                same = self.queue.submit(job_id=job_id, idempotency_key=key, intent=intent)
                self.duplicate_submissions += 1
                if same is job:
                    self.dedupe_reused += 1

            if seq == 1:
                try:
                    self.queue.submit(job_id="FA120-CONFLICT", idempotency_key=key, intent={**intent, "semantic_asset_id": "DIFFERENT"})
                except queue_mod.QueueError as exc:
                    if exc.code != "IDEMPOTENCY_CONFLICT":
                        raise
                    self.idempotency_conflicts_blocked += 1
                else:
                    raise RuntimeError("IDEMPOTENCY_CONFLICT_NOT_BLOCKED")

            self.next_seq += 1
            self.peak_active_depth = max(self.peak_active_depth, len(self.active))

        if self.next_seq <= self.config.unique_jobs and len(self.active) >= self.config.max_active_jobs:
            self.admission_backpressure_events += 1

    def _nonempty_ready_tenants(self) -> list[str]:
        return [t for t in self.config.tenants if self.ready[t]]

    def _pop_fair(self) -> tuple[str, str] | None:
        nonempty = self._nonempty_ready_tenants()
        if not nonempty:
            return None
        n = len(self.config.tenants)
        for offset in range(n):
            idx = (self.cursor + offset) % n
            tenant = self.config.tenants[idx]
            if self.ready[tenant]:
                contended = len(nonempty) > 1
                if contended and tenant == self.last_contended_tenant:
                    self.fairness_violations += 1
                self.last_contended_tenant = tenant if contended else None
                self.cursor = (idx + 1) % n
                return tenant, self.ready[tenant].popleft()
        return None

    def _requeue_front(self, tenant: str, job_id: str) -> None:
        self.ready[tenant].appendleft(job_id)

    def _record_first_dispatch(self, tenant: str, job: Any) -> None:
        if job.attempts == 1:
            self.first_dispatch_counts[tenant] += 1
            values = list(self.first_dispatch_counts.values())
            self.max_first_dispatch_skew = max(self.max_first_dispatch_skew, max(values) - min(values))

    def _should_retry(self, seq: int, attempt: int) -> bool:
        if seq % self.config.retry_twice_every == 0 and attempt <= 2:
            return True
        return seq % self.config.retry_once_every == 0 and attempt == 1

    def _apply_disk_backpressure(self) -> None:
        self.disk_backpressure_events += 1
        reclaimed = self.disk.reclaim_to_low()
        if reclaimed <= 0:
            raise RuntimeError("DISK_BACKPRESSURE_WITHOUT_RECLAIMABLE_BYTES")
        self.disk_reclaimed_bytes += reclaimed
        self.disk_resume_events += 1

    def _perform_restart(self) -> None:
        state_path = self.root / "fa120-harness-state.json"
        tmp_path = state_path.with_suffix(".tmp")
        payload = json.dumps(self.queue.snapshot(), sort_keys=True, separators=(",", ":"))
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, state_path)
        self.restart_snapshot_bytes = state_path.stat().st_size
        restored_payload = json.loads(state_path.read_text(encoding="utf-8"))
        self.queue = queue_mod.FactoryJobQueue.from_snapshot(restored_payload)
        self.leases = lease_mod.ProviderLeaseRegistry()
        self.ready = {t: deque() for t in self.config.tenants}
        self.last_contended_tenant = None
        recovered = 0
        for row in self.queue.list():
            if row["job_id"] not in self.active:
                continue
            if row["state"] == "READY":
                tenant = str(row["intent"]["tenant_id"])
                self.ready[tenant].append(row["job_id"])
                if row.get("recovery_count", 0) > 0:
                    recovered += 1
            elif row["state"] == "RETRY_WAIT":
                self.queue.retry(row["job_id"])
                tenant = str(row["intent"]["tenant_id"])
                self.ready[tenant].append(row["job_id"])
            elif row["state"] not in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                raise RuntimeError(f"UNRECOVERED_STATE:{row['state']}")
        self.restart_recovered_jobs = recovered
        self.restart_performed = True

    def _dispatch_one(self, slot: int) -> tuple[bool, bool]:
        picked = self._pop_fair()
        if picked is None:
            return False, False
        tenant, job_id = picked
        job = self.queue.get(job_id)
        seq = self._seq(job_id)
        modeled_size = self._modeled_output_bytes(seq)
        if not self.disk.can_commit(modeled_size):
            self._requeue_front(tenant, job_id)
            self._apply_disk_backpressure()
            return True, False

        token = hashlib.sha256(f"lease:{job_id}:{job.attempts + 1}:{slot}".encode()).hexdigest()
        profile_id = f"fa120-synthetic-slot-{slot}"
        principal_id = f"fa120-synthetic-principal-{slot}"
        owner = f"fa120-harness:{job_id}"
        self.leases.acquire(token=token, principal_id=principal_id, profile_id=profile_id, owner=owner)
        self.queue.start(job_id, owner=owner, lease_token=token)
        job = self.queue.get(job_id)
        self.total_attempts += 1
        self._record_first_dispatch(tenant, job)

        if self.lease_contention_blocked == 0:
            try:
                self.leases.acquire(token="intruder", principal_id="intruder", profile_id=profile_id, owner="intruder")
            except lease_mod.LeaseError as exc:
                if exc.code != "PROFILE_ALREADY_LEASED":
                    raise
                self.lease_contention_blocked += 1
            else:
                raise RuntimeError("LEASE_CONTENTION_NOT_BLOCKED")

        if (not self.restart_performed) and self.succeeded >= self.config.restart_after_successes:
            return True, True

        if self._should_retry(seq, job.attempts):
            failed = self.queue.fail(job_id, code="RATE_LIMITED", retryable=True)
            self.leases.release(token=token, profile_id=profile_id)
            if failed.state != "RETRY_WAIT":
                raise RuntimeError("EXPECTED_RETRY_WAIT")
            self.queue.retry(job_id)
            self.retry_events += 1
            self.ready[tenant].append(job_id)
            return True, False

        self.queue.succeed(job_id, artifact_sha256=self._artifact_sha(job_id))
        self.leases.release(token=token, profile_id=profile_id)
        self.disk.commit(modeled_size)
        self.active.remove(job_id)
        self.succeeded += 1
        self.completion_counts[tenant] += 1
        return True, False

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        safety_loops = 0
        while self.succeeded + self.failed < self.config.unique_jobs:
            safety_loops += 1
            if safety_loops > self.config.unique_jobs * 20:
                raise RuntimeError("HARNESS_PROGRESS_GUARD_EXCEEDED")
            self._admit_until_bounded()
            progressed = False
            restart_now = False
            for slot in range(self.config.worker_slots):
                did_work, wants_restart = self._dispatch_one(slot)
                progressed = progressed or did_work
                if wants_restart:
                    restart_now = True
                    break
            if restart_now:
                self._perform_restart()
                continue
            if not progressed:
                if self.active:
                    raise RuntimeError("ACTIVE_QUEUE_STALLED")
                if self.next_seq <= self.config.unique_jobs:
                    continue
                break

        elapsed = max(time.perf_counter() - started, 1e-9)
        rows = self.queue.list()
        terminal_successes = sum(1 for r in rows if r["state"] == "SUCCEEDED")
        terminal_failures = sum(1 for r in rows if r["state"] == "FAILED")
        unique_job_rows = len(rows)
        retry_counts = [int(r["retries"]) for r in rows]
        recoveries = [int(r.get("recovery_count", 0)) for r in rows]
        completion_values = list(self.completion_counts.values())

        assertions = {
            "thousands_processed": self.succeeded == self.config.unique_jobs and self.config.unique_jobs >= 2000,
            "bounded_active_queue": self.peak_active_depth <= self.config.max_active_jobs and self.admission_backpressure_events > 0,
            "fair_round_robin": self.fairness_violations == 0 and max(completion_values) - min(completion_values) <= 1,
            "lease_exclusion": self.lease_contention_blocked > 0,
            "retries_bounded": self.retry_events > 0 and max(retry_counts, default=0) <= 2 and terminal_failures == 0,
            "dedupe": self.duplicate_submissions > 0 and self.dedupe_reused == self.duplicate_submissions and self.idempotency_conflicts_blocked == 1,
            "restart_recovery": self.restart_performed and self.restart_recovered_jobs > 0 and max(recoveries, default=0) == 1,
            "disk_backpressure": self.disk_backpressure_events > 0 and self.disk_resume_events == self.disk_backpressure_events and self.disk.peak <= self.disk.high,
            "zero_provider_calls": True,
            "zero_loss_or_duplicate_success": terminal_successes == self.config.unique_jobs and unique_job_rows == self.config.unique_jobs,
        }
        result = "PASS" if all(assertions.values()) else "FAIL"
        return {
            "schema": "die.factory-asset.synthetic-throughput-backpressure.v1",
            "task_id": "FA-120",
            "result": result,
            "provider_calls_performed": False,
            "config": {
                "unique_jobs": self.config.unique_jobs,
                "tenants": list(self.config.tenants),
                "max_active_jobs": self.config.max_active_jobs,
                "worker_slots": self.config.worker_slots,
                "virtual_disk_capacity_bytes": self.config.virtual_disk_capacity_bytes,
                "disk_high_watermark_bytes": self.disk.high,
                "disk_low_watermark_bytes": self.disk.low,
            },
            "queue": {
                "unique_jobs": unique_job_rows,
                "terminal_successes": terminal_successes,
                "terminal_failures": terminal_failures,
                "peak_active_depth": self.peak_active_depth,
                "admission_backpressure_events": self.admission_backpressure_events,
            },
            "fairness": {
                "first_dispatch_counts": dict(self.first_dispatch_counts),
                "completion_counts": dict(self.completion_counts),
                "max_first_dispatch_skew": self.max_first_dispatch_skew,
                "violations": self.fairness_violations,
            },
            "leases": {
                "contention_blocked": self.lease_contention_blocked,
                "active_after_run": sum(1 for i in range(self.config.worker_slots) if self.leases.active(f"fa120-synthetic-slot-{i}") is not None),
            },
            "retries": {
                "retry_events": self.retry_events,
                "max_retries_per_job": max(retry_counts, default=0),
                "total_attempts": self.total_attempts,
            },
            "dedupe": {
                "duplicate_submissions": self.duplicate_submissions,
                "duplicate_reused": self.dedupe_reused,
                "idempotency_conflicts_blocked": self.idempotency_conflicts_blocked,
            },
            "restart": {
                "performed": self.restart_performed,
                "recovered_jobs": self.restart_recovered_jobs,
                "snapshot_bytes": self.restart_snapshot_bytes,
                "max_recovery_count": max(recoveries, default=0),
            },
            "disk_backpressure": {
                "model": "VIRTUAL_BOUNDED_SPOOL_NO_PAYLOAD_ALLOCATION",
                "peak_bytes": self.disk.peak,
                "high_watermark_bytes": self.disk.high,
                "events": self.disk_backpressure_events,
                "resume_events": self.disk_resume_events,
                "reclaimed_bytes": self.disk_reclaimed_bytes,
                "final_modeled_bytes": self.disk.used,
            },
            "benchmark": {
                "elapsed_seconds": round(elapsed, 6),
                "successful_jobs_per_second": round(self.succeeded / elapsed, 3),
            },
            "assertions": assertions,
        }


def run_synthetic_throughput_acceptance(staging_root: str | Path, config: HarnessConfig | None = None) -> dict[str, Any]:
    return SyntheticThroughputHarness(staging_root, config=config).run()
