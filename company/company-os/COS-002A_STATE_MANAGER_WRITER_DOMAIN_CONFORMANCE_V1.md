# COS-002A ? State Manager Writer-Domain Conformance v1

Status: **DONE / PASS**
Date: 2026-09-09
Parent: `COS-002`
Gate satisfied: `STATE_MANAGER_WRITER_DOMAIN_CONFORMANCE_PASS`

## 1. Purpose

Prove mechanically that DIE preserves **one logical canonical company-state writer** while allowing multiple bounded writer adapters for distinct Company Truth domains. This task does not promote Mission Control, amend the Constitution, disposition Hermes, or grant new authority.

## 2. Canonical sovereignty

Current identity canon declares:

```text
canonical_state_writer = die-state-manager
sole_physical_writer_count = 1
```

Multiple actors may be semantic authors, but canonical mutations must cross the State Manager boundary.

## 3. Current writer-domain map

| Domain | Physical implementation | Logical writer | Standing |
|---|---|---|---|
| Global append-only events | `bin/die_event.py` -> `state/EVENTS.jsonl` | `die-state-manager` | PASS |
| Global append-only decisions | `bin/die_event.py` -> `state/DECISIONS.jsonl` | `die-state-manager` | PASS |
| Global economics store | `state/ECONOMICS.jsonl` | reserved for `die-state-manager` | **No live writer implemented currently** |
| H01 Factory canonical asset registry | `company/factory-asset/lib/factory_state_manager.py` | same State Manager (`DIE_STATE_MANAGER` token) | PASS |
| Kanban/operational views | governed projection/runtime state | not canonical Company Truth | non-sovereign projection |
| `state/projection/*` | bridge projection | not canonical Company Truth | non-sovereign projection |
| Mission Control SQLite state | Mission Control internal DB | Mission Control control-plane state only | not Company Truth |

The existence of multiple implementation modules does **not** create multiple sovereign writers. `DIE_STATE_MANAGER` in Factory Asset is the H01 adapter token for the same logical service whose canonical identity is `die-state-manager`.

## 4. Global append-only stores

Static conformance scanning finds write-capable canonical paths only in:

```text
bin/die_event.py
  state/EVENTS.jsonl
  state/DECISIONS.jsonl
```

No production Python module outside the declared State Manager writer was detected writing these global canonical stores.

References in cron/operator/projection code are reads or writes to non-canonical projection/receipt/cursor surfaces, not direct Company Truth mutation.

## 5. Decision Gateway

Runtime cognition does not receive raw canonical-write ownership. `bridge/income_os_bridge/decision_gateway.py` declares:

```text
WRITER_ID = die-state-manager
```

and accepts only normalized `validated_not_committed` requests. Rejected requests return:

```text
canonical_mutation = false
```

The bounded commit implementation is `die_event.commit_normalized_decision`, and committed records identify:

```text
committed_by = die-state-manager
```

Targeted Decision Gateway acceptance: **14/14 PASS**.

## 6. Factory State Manager adapter

The Factory Asset registry has a separate domain adapter because its canonical object is a structured asset registry rather than a global JSONL event stream.

It declares:

```text
WRITER = DIE_STATE_MANAGER
```

and fails closed for any different `writer_id` with `WRITER_ID_FORBIDDEN`.

The governed canary registry itself declares:

```text
canonical_writer = DIE_STATE_MANAGER
```

Factory writer acceptance: **11/11 PASS** across FA-203 registry QA and FA-204 metadata/rights tests.

This adapter is therefore a domain implementation of the same logical writer, not a second Company State Manager service.

## 7. Mission Control boundary

Audited Mission Control canonical source:

```text
5557e3738cc11d82c53dfb68072b1f09a388e22a
```

Static scan of Mission Control `src/`, `scripts/`, and `config/` found **zero references** to:

```text
state/EVENTS.jsonl
DECISIONS.jsonl
ECONOMICS.jsonl
die_event.py
governed-canary-assets.v1.json
```

Therefore its SQLite mission/task/lease/wake/review state is a separate **operational control-plane domain**. It does not currently implement a hidden direct Company Truth writer.

This proves the intended boundary:

```text
Mission Control internal state
!=
DIE canonical company operational truth
```

## 8. Economics warning

`state/ECONOMICS.jsonl` exists as a canonical store, but current code has no detected live physical writer implementation for it.

This is recorded as:

```text
W_ECONOMICS_WRITER_NOT_IMPLEMENTED_CURRENTLY
```

It is **not** an exclusivity failure because no competing writer exists. It is an implementation-completeness warning: future ECON ingestion must not append directly from Mission Control, Hermes, an observer, a worker, or a marketplace connector. A State Manager economics adapter/commit path must exist before live canonical economic writes are enabled.

## 9. Executable guard

Canonical checker:

```text
bin/die_state_writer_conformance.py
```

It verifies:

1. identity registry has exactly one `sole_physical_writer`;
2. that writer is `die-state-manager`;
3. no production Python module outside `bin/die_event.py` writes global canonical JSONL stores;
4. Factory registry uses the same logical State Manager token and fails closed on writer mismatch;
5. Decision Gateway names `die-state-manager` and preserves rejection no-mutation semantics;
6. optional Mission Control source scan has no Company Truth store coupling.

Negative tests prove:

```text
competing global writer -> FAIL
second sole physical writer -> FAIL
```

## 10. Authority implications

This PASS does **not** mean:

- Mission Control is constitutionally promoted;
- Mission Control may write Company Truth directly;
- Hermes is demoted or retired;
- ECON ingestion is live;
- Founder ratification is complete;
- delegated execution is accepted;
- new spend/red-zone authority exists.

It means only that the **writer-domain sovereignty required by COS-002 is conformant at the audited versions**.

## 11. COS-004 gate effect

The former external gate:

```text
STATE_MANAGER_WRITER_DOMAIN_CONFORMANCE_PASS
```

is now represented canonically by explicit dependency:

```text
COS-004 depends_on COS-002A
```

Remaining COS-004 gates are still:

```text
MC-008J_FULLY_UNATTENDED_24X7_ACCEPTED
MC-009D_DELEGATED_EXECUTION_ACCEPTED
FOUNDER_RATIFICATION_COS002_PACKET
```

## 12. Acceptance

**PASS.** Current global Company Truth writers and H01 Factory canonical registry commits resolve to one logical DIE State Manager; direct competing global-store writes are mechanically rejected by conformance tests; Mission Control remains a separate operational-state domain with no audited direct Company Truth coupling. The missing live economics writer is preserved as a warning and may not be bypassed by future ingestion.
