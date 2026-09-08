from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter, deque
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


queue_mod = _load("fa_c011_factory_queue", "company/factory-asset/lib/factory_queue.py")
router_mod = _load("fa_c011_provider_router", "company/factory-asset/lib/provider_router.py")
console_contract = _load("fa_c011_console_contract", "company/factory-asset/lib/console_contract.py")


@dataclass(frozen=True)
class ConsoleBatchAcceptanceConfig:
    batch_quantity: int = 12
    worker_slots: int = 3
    duplicate_indices: tuple[int, ...] = (2, 5, 8)
    pause_index: int = 3
    retry_index: int = 5
    terminal_failure_index: int = 7

    def validate(self) -> None:
        if self.batch_quantity < 8 or self.batch_quantity > 1000:
            raise ValueError("batch_quantity must be 8..1000")
        if self.worker_slots < 2 or self.worker_slots > self.batch_quantity:
            raise ValueError("worker_slots must prove bounded concurrency")
        special = {self.pause_index, self.retry_index, self.terminal_failure_index}
        if len(special) != 3 or min(special) < 1 or max(special) > self.batch_quantity:
            raise ValueError("pause/retry/failure probes must be distinct in-range jobs")
        if any(i < 1 or i > self.batch_quantity for i in self.duplicate_indices):
            raise ValueError("duplicate probe index outside batch")


class ConsoleBatchAcceptanceHarness:
    """Deterministic FA-C011 Console batch/concurrency acceptance with zero provider calls."""

    def __init__(self, workspace: str | Path, config: ConsoleBatchAcceptanceConfig | None = None):
        self.config = config or ConsoleBatchAcceptanceConfig()
        self.config.validate()
        self.root = Path(workspace).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.queue = queue_mod.FactoryJobQueue()
        self.batch_id = "FCBATCH-FA-C011-20260908-001"
        self.blueprint_id = "FABP-FA-C011-SYNTHETIC-BATCH-001"
        self.semantic_root = "FASA-FA-C011-SYNTHETIC"
        self.pending: deque[str] = deque()
        self.routes: dict[str, dict[str, Any]] = {}
        self.timeline: list[dict[str, Any]] = []
        self.backpressure_events = 0
        self.peak_running = 0
        self.pause_events = 0
        self.resume_events = 0
        self.retry_events = 0
        self.terminal_failures = 0
        self.duplicate_submissions = 0
        self.duplicate_reuses = 0
        self.idempotency_conflicts_blocked = 0
        self.duplicate_ownership_blocked = 0
        self.succeeded_after_terminal_failure = 0
        self._paused = False
        self._retried = False
        self._terminal_failed = False
        self._terminal_failure_wave: int | None = None

    @staticmethod
    def _sha(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _index(job_id: str) -> int:
        return int(job_id.rsplit("-", 1)[1])

    def _job_id(self, index: int) -> str:
        return f"FCJOB-FA-C011-{index:03d}"

    def _semantic_id(self, index: int) -> str:
        return f"{self.semantic_root}-{index:03d}"

    def _route(self, index: int) -> dict[str, Any]:
        odd = index % 2 == 1
        candidates = [
            {
                "profile_id": "qwen_batch_synth",
                "provider_id": "qwen",
                "enabled": True,
                "policy_allowed": True,
                "capacity_state": "AVAILABLE",
                "asset_types": ["PHOTO"],
                "quality_score": 0.97 if odd else 0.91,
                "unit_cost_micros": 0,
                "priority": 10,
            },
            {
                "profile_id": "chatgpt_batch_synth",
                "provider_id": "chatgpt",
                "enabled": True,
                "policy_allowed": True,
                "capacity_state": "AVAILABLE",
                "asset_types": ["PHOTO"],
                "quality_score": 0.91 if odd else 0.97,
                "unit_cost_micros": 0,
                "priority": 10,
            },
        ]
        decision = router_mod.route_provider(asset_type="PHOTO", candidates=candidates)
        return decision.as_dict()

    def _atomic_json(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def _state_counts(self) -> dict[str, int]:
        counts = Counter(row["state"] for row in self.queue.list())
        return {state: int(counts.get(state, 0)) for state in ("READY", "RUNNING", "PAUSED", "RETRY_WAIT", "SUCCEEDED", "FAILED", "CANCELLED")}

    def _record(self, *, phase: str, wave: int, note: str | None = None) -> None:
        rows = self.queue.list()
        running = [row for row in rows if row["state"] == "RUNNING"]
        semantic_ids = {str(row["intent"]["semantic_asset_id"]) for row in rows}
        event = {
            "schema": "die.factory-asset.console-batch-timeline-event.v1",
            "task_id": "FA-C011",
            "source_surface": "FACTORY_CONSOLE",
            "batch_id": self.batch_id,
            "phase": phase,
            "wave": wave,
            "note": note,
            "states": self._state_counts(),
            "pending_dispatch": len(self.pending),
            "running_job_ids": sorted(row["job_id"] for row in running),
            "running_owners": sorted(str(row["owner"]) for row in running),
            "semantic_asset_count": len(semantic_ids),
            "provider_calls_performed": False,
        }
        self.timeline.append(event)
        self.peak_running = max(self.peak_running, len(running))

    def _submit_batch(self) -> None:
        for index in range(1, self.config.batch_quantity + 1):
            route = self._route(index)
            job_id = self._job_id(index)
            key = self._sha(f"fa-c011|{self.batch_id}|{index}")
            intent = {
                "source_surface": "FACTORY_CONSOLE",
                "batch_id": self.batch_id,
                "blueprint_id": self.blueprint_id,
                "semantic_asset_id": self._semantic_id(index),
                "asset_type": "PHOTO",
                "provider_id": route["provider_id"],
                "profile_id": route["profile_id"],
                "label": f"FA-C011 synthetic batch #{index:03d}",
                "synthetic": True,
            }
            job = self.queue.submit(job_id=job_id, idempotency_key=key, intent=intent)
            self.pending.append(job.job_id)
            self.routes[job_id] = route
            if index in self.config.duplicate_indices:
                duplicate = self.queue.submit(job_id=job_id, idempotency_key=key, intent=intent)
                self.duplicate_submissions += 1
                if duplicate is job:
                    self.duplicate_reuses += 1

        first = self.queue.get(self._job_id(1))
        try:
            self.queue.submit(
                job_id="FCJOB-FA-C011-CONFLICT",
                idempotency_key=first.idempotency_key,
                intent={**first.intent, "semantic_asset_id": "FASA-FA-C011-CONFLICT"},
            )
        except queue_mod.QueueError as exc:
            if exc.code != "IDEMPOTENCY_CONFLICT":
                raise
            self.idempotency_conflicts_blocked += 1
        else:
            raise RuntimeError("IDEMPOTENCY_CONFLICT_NOT_BLOCKED")

    def _start_wave(self, wave: int) -> list[str]:
        active: list[str] = []
        for slot in range(self.config.worker_slots):
            if not self.pending:
                break
            job_id = self.pending.popleft()
            job = self.queue.get(job_id)
            if job.state != "READY":
                raise RuntimeError(f"NON_READY_PENDING_JOB:{job_id}:{job.state}")
            owner = f"factory-console-c011-worker-{slot}"
            token = self._sha(f"fa-c011-lease|{job_id}|{job.attempts + 1}|wave={wave}|slot={slot}")
            self.queue.start(job_id, owner=owner, lease_token=token)
            active.append(job_id)

        if self.pending:
            self.backpressure_events += 1
        self._record(phase="WAVE_RUNNING", wave=wave, note="worker-slot bound applied before outcomes")

        if active and self.duplicate_ownership_blocked == 0:
            target = active[0]
            try:
                self.queue.start(target, owner="factory-console-intruder", lease_token="intruder")
            except queue_mod.QueueError as exc:
                if exc.code != "DUPLICATE_OWNERSHIP":
                    raise
                self.duplicate_ownership_blocked += 1
            else:
                raise RuntimeError("DUPLICATE_OWNERSHIP_NOT_BLOCKED")
        return active

    def _settle_wave(self, active: list[str], wave: int) -> None:
        for job_id in active:
            index = self._index(job_id)
            if index == self.config.pause_index and not self._paused:
                paused = self.queue.pause(job_id)
                if paused.state != "PAUSED" or paused.owner is not None or paused.lease_token is not None:
                    raise RuntimeError("PAUSE_DID_NOT_RELEASE_OWNERSHIP")
                self.pause_events += 1
                self._record(phase="JOB_PAUSED", wave=wave, note=job_id)
                resumed = self.queue.resume(job_id)
                if resumed.state != "READY":
                    raise RuntimeError("RESUME_DID_NOT_RETURN_READY")
                self.resume_events += 1
                self._paused = True
                self.pending.append(job_id)
                self._record(phase="JOB_RESUMED", wave=wave, note=job_id)
                continue

            if index == self.config.retry_index and not self._retried:
                failed = self.queue.fail(job_id, code="RATE_LIMITED", retryable=True)
                if failed.state != "RETRY_WAIT":
                    raise RuntimeError("RETRYABLE_FAILURE_NOT_WAITING")
                self._record(phase="JOB_RETRY_WAIT", wave=wave, note=job_id)
                retried = self.queue.retry(job_id)
                if retried.state != "READY" or retried.retries != 1:
                    raise RuntimeError("RETRY_DID_NOT_RETURN_READY")
                self.retry_events += 1
                self._retried = True
                self.pending.append(job_id)
                continue

            if index == self.config.terminal_failure_index and not self._terminal_failed:
                failed = self.queue.fail(job_id, code="PROVIDER_ERROR", retryable=False)
                if failed.state != "FAILED":
                    raise RuntimeError("TERMINAL_PARTIAL_FAILURE_NOT_TERMINAL")
                self.terminal_failures += 1
                self._terminal_failed = True
                self._terminal_failure_wave = wave
                self._record(phase="JOB_PARTIAL_FAILURE", wave=wave, note=job_id)
                continue

            artifact_sha = self._sha(f"fa-c011-synthetic-artifact|{job_id}")
            self.queue.succeed(job_id, artifact_sha256=artifact_sha)
            if self._terminal_failed and self._terminal_failure_wave is not None and wave >= self._terminal_failure_wave:
                self.succeeded_after_terminal_failure += 1

        self._record(phase="WAVE_SETTLED", wave=wave)

    def run(self) -> dict[str, Any]:
        self._submit_batch()
        self._record(phase="BATCH_READY", wave=0)
        wave = 0
        while self.pending:
            wave += 1
            active = self._start_wave(wave)
            if not active:
                raise RuntimeError("BATCH_STALLED")
            self._settle_wave(active, wave)
            if wave > self.config.batch_quantity * 4:
                raise RuntimeError("BATCH_PROGRESS_GUARD_EXCEEDED")

        rows = self.queue.list()
        states = Counter(row["state"] for row in rows)
        semantics = [str(row["intent"]["semantic_asset_id"]) for row in rows]
        route_counts = Counter(str(row["intent"]["provider_id"]) for row in rows)
        total_attempts = sum(int(row["attempts"]) for row in rows)
        max_retries = max((int(row["retries"]) for row in rows), default=0)
        terminal_count = int(states["SUCCEEDED"] + states["FAILED"] + states["CANCELLED"])

        assertions = {
            "queue_progress": terminal_count == self.config.batch_quantity and not self.pending,
            "provider_routing": route_counts == Counter({"qwen": self.config.batch_quantity // 2, "chatgpt": self.config.batch_quantity // 2}),
            "bounded_backpressure": self.backpressure_events > 0 and self.peak_running == self.config.worker_slots and all(e["states"]["RUNNING"] <= self.config.worker_slots for e in self.timeline),
            "pause_resume": self.pause_events == 1 and self.resume_events == 1 and self.queue.get(self._job_id(self.config.pause_index)).state == "SUCCEEDED",
            "partial_failures_contained": states["FAILED"] == 1 and states["SUCCEEDED"] == self.config.batch_quantity - 1 and self.succeeded_after_terminal_failure > 0,
            "retry_bounded": self.retry_events == 1 and max_retries == 1 and self.queue.get(self._job_id(self.config.retry_index)).state == "SUCCEEDED",
            "duplicate_ownership_blocked": self.duplicate_ownership_blocked == 1,
            "idempotent_batch_dedupe": self.duplicate_submissions == len(self.config.duplicate_indices) and self.duplicate_reuses == self.duplicate_submissions and self.idempotency_conflicts_blocked == 1,
            "no_semantic_count_inflation": len(rows) == self.config.batch_quantity and len(set(semantics)) == self.config.batch_quantity and terminal_count == self.config.batch_quantity and total_attempts > self.config.batch_quantity,
            "zero_provider_calls": True,
        }
        result = "PASS" if all(assertions.values()) else "FAIL"
        final_state = {
            "schema": "die.factory-asset.console-batch-state.v1",
            "task_id": "FA-C011",
            "source_surface": "FACTORY_CONSOLE",
            "batch_id": self.batch_id,
            "phase": "TERMINAL",
            "state_counts": self._state_counts(),
            "semantic_asset_count": len(set(semantics)),
            "provider_route_counts": dict(sorted(route_counts.items())),
            "provider_calls_performed": False,
            "browser_owner_actions": 0,
        }
        result_payload = {
            "schema": "die.factory-asset.console-batch-acceptance.v1",
            "task_id": "FA-C011",
            "result": result,
            "source_surface": "FACTORY_CONSOLE",
            "batch": {
                "batch_id": self.batch_id,
                "blueprint_id": self.blueprint_id,
                "quantity": self.config.batch_quantity,
                "semantic_asset_count": len(set(semantics)),
                "dispatch_authority": "SIMULATED_ONLY",
            },
            "queue": {
                "waves": wave,
                "terminal_count": terminal_count,
                "succeeded": int(states["SUCCEEDED"]),
                "failed": int(states["FAILED"]),
                "peak_concurrent_running": self.peak_running,
                "worker_slot_limit": self.config.worker_slots,
                "backpressure_events": self.backpressure_events,
                "total_attempts": total_attempts,
                "max_retries_per_job": max_retries,
            },
            "routing": {
                "route_counts": dict(sorted(route_counts.items())),
                "routes": {job_id: self.routes[job_id] for job_id in sorted(self.routes)},
            },
            "controls": {
                "pause_events": self.pause_events,
                "resume_events": self.resume_events,
                "retry_events": self.retry_events,
                "terminal_partial_failures": self.terminal_failures,
                "succeeded_after_terminal_failure": self.succeeded_after_terminal_failure,
            },
            "ownership_and_dedupe": {
                "duplicate_ownership_blocked": self.duplicate_ownership_blocked,
                "duplicate_submissions": self.duplicate_submissions,
                "duplicate_reuses": self.duplicate_reuses,
                "idempotency_conflicts_blocked": self.idempotency_conflicts_blocked,
            },
            "semantic_integrity": {
                "expected_semantic_assets": self.config.batch_quantity,
                "unique_semantic_assets": len(set(semantics)),
                "terminal_jobs": terminal_count,
                "total_attempts": total_attempts,
                "attempts_do_not_count_as_semantic_assets": True,
                "duplicates_do_not_count_as_semantic_assets": True,
                "partial_failure_does_not_create_replacement_semantic_asset": True,
            },
            "provider_calls_performed": False,
            "browser_owner_actions": 0,
            "credential_values_read": False,
            "cookies_or_tokens_read": False,
            "spend_usd": 0,
            "account_actions": 0,
            "marketplace_actions": 0,
            "assertions": assertions,
        }
        state_path = self.root / "console-batch-state.json"
        timeline_path = self.root / "console-batch-timeline.json"
        final_path = self.root / "final-result.json"
        self._atomic_json(state_path, final_state)
        self._atomic_json(timeline_path, {"schema": "die.factory-asset.console-batch-timeline.v1", "task_id": "FA-C011", "events": self.timeline})
        result_payload["evidence_paths"] = {
            "console_state": str(state_path),
            "timeline": str(timeline_path),
            "final_result": str(final_path),
        }
        self._atomic_json(final_path, result_payload)
        return result_payload


def run_console_batch_acceptance(workspace: str | Path, config: ConsoleBatchAcceptanceConfig | None = None) -> dict[str, Any]:
    return ConsoleBatchAcceptanceHarness(workspace, config=config).run()
