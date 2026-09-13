# DIE H01 Brave Round-Robin Scheduler v1

Status: **H01-026 DONE / PASS**
Date: 2026-09-12

## Architecture

H01-026 schedules work at two different levels:

1. **Global multi-UDD admission** decides which idle UDD may accept a lease. Current Founder-approved ceiling is five live UDD owners; topology absolute maximum remains twenty.
2. **Per-UDD round-robin** chooses one eligible sibling profile and one eligible provider for that UDD.

A UDD is never a five-browser cluster. It owns five persistent sibling identities, but at most one sibling profile may be active and that profile may own exactly one committed provider tab/job. Different UDDs may execute concurrently within the current global admission ceiling.

```text
queue
  -> global admission (current <=5 UDD owners)
      -> idle UDD
          -> next READY sibling profile
          -> next READY/non-cooled-down provider
          -> durable lease
          -> exactly-once dispatch claim
          -> H01-025 browser runtime
          -> durable terminal result
          -> release scheduler lease
```

## Readiness and provider eligibility

Provisioned is not equivalent to authenticated. At H01-026 acceptance only `h01-web-p001` has sufficient live authentication proof, therefore it is the only profile marked `READY`. The remaining 99 stay `NOT_READY` until Founder/manual authentication is actually available.

Provider eligibility comes from H01-107 observed results. Claude, ChatGPT, Qwen, Gemini, Manus and Copilot are READY. Grok remains disabled from its bounded UNSUPPORTED result; Duck.ai remains disabled from its DEFERRED timeout. H01-026 does not promote them.

## Lease state machine

```text
LEASED -> DISPATCH_CLAIMED -> TERMINAL
```

`claim-dispatch` is the exactly-once authority boundary. The first valid claim returns `dispatch_authorized=true`. Repeating the same claim returns `ALREADY_DISPATCHED` with `dispatch_authorized=false`. Re-acquiring a completed dispatch ID returns `ALREADY_TERMINAL` and may not create a new lease.

The scheduler keeps its own durable lease ledger while H01-025 remains the sole browser owner. Before lease issuance it also verifies the H01-025 UDD runtime mutex is free. H01-025 then owns the actual browser-level flock and single-tab lifecycle.

## Concurrency policy

The policy contains both `global_max_live_udd_owners` and `founder_approved_max_live_udd_owners`. The scheduler rejects a configured live cap above the Founder-approved ceiling. Today both are 5. H01-029 later accepted exactly five simultaneous UDD owners under Founder policy. H01-027's older 8/10-owner expansion acceptance is superseded and must not be executed; any future ceiling increase requires a new explicit Founder-governed scale task. Absolute topology remains 20 UDD owners.

## Live canary

The live canary issued a lease for `s01/p001/Claude`, authorized the first dispatch claim, rejected the duplicate claim, completed it as CANCELLED without provider submission, then rejected recreation of the same dispatch ID as already terminal. While the real `s01` H01-025 mutex was externally held, a fresh lease attempt failed closed with `E_NO_ELIGIBLE_UDD`. Final active lease count returned to zero.

No browser was opened and no provider prompt was dispatched by this canary. No cookies, tokens or session bytes were read.
