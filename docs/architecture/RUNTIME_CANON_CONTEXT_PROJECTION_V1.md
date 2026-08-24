# Runtime Canon Context Projection v1

Status: IMPLEMENTED ON FEATURE BRANCH
Authority: `CONSTITUTION.md`, `COMPANY_BRAIN.md`
Manifest: `company/runtime-canon-context-v1.json`

## 1. Decision

Executive and Division-01 cannot read the repository, so a wake message that
names canon files cannot prove assimilation. The existing principal-pinned
`context_snapshot` now includes a bounded `canon_context` surface. No MCP tool,
port, writer, or transport is added.

```text
allowlisted repo docs + exact SHA-256
-> governed manifest validation
-> principal-specific semantic facts
-> existing context_snapshot
-> deterministic snapshot ID + optional HMAC
-> independent fresh-context receipt
```

## 2. Projection contract

The projection supports only `chatgpt-plus-executive` at
`company_portfolio` scope and `division-head-division01` at `single_division`
scope. It returns:

- exact repository commit SHA and manifest SHA-256;
- the three required M-001 canon documents and two supporting inputs, each
  named by repository-relative path, classification, SHA-256, and
  `load_status: VERIFIED`;
- bounded common and role-specific decision facts with evidence labels;
- a dated five-marketplace plus Magnific digest;
- a formula-result digest from the quantity workbook, explicitly labeled
  `HYPOTHESIS` and not ERVA, net profit, run-rate, or feasibility evidence;
- the fields required for a later assimilation receipt.

The projection never returns raw document bytes, host paths, credentials,
repository tools, state-write capability, or execution authority.

## 3. Fail-closed controls

`company/runtime-canon-context-v1.json` is a strict-schema allowlist. Runtime
construction fails if its shape, principal routing, classifications, byte
limits, repository revision, source paths, source files, or hashes differ from
the governed contract.

| Code | Meaning |
| --- | --- |
| `E_CANON_UNAVAILABLE` | Manifest or allowlisted source cannot be read |
| `E_CANON_INVALID` | Manifest shape, routing, path, or classification is invalid |
| `E_CANON_HASH_MISMATCH` | An allowlisted source differs from its pinned digest |
| `E_CANON_REPO_REVISION` | Exact repository SHA cannot be resolved |
| `E_CANON_SCOPE_DENIED` | Principal or scope has no canon projection profile |
| `E_CANON_TOO_LARGE` | Projected semantic surface exceeds its byte bound |

Because `canon_context` is inside the existing snapshot data, its facts and
document digests are covered by the deterministic snapshot ID and, when
configured, the existing HMAC integrity proof.

## 4. Assimilation and authority

`load_status: VERIFIED` proves only that the server validated and projected the
pinned canon into a fresh snapshot for the correct principal. Each principal
must still answer an independent fresh-context probe and emit a receipt with
principal ID, repository SHA, documents, snapshot ID/as-of, probe results, and
`PASS|FAIL`.

A listening port or wake success proves transport only. Current mission state,
decisions, deadlines, evidence, and blockers remain in the other signed
snapshot surfaces. Worth-Making remains blocked until the Division-01 receipt
is `PASS`; this feature itself authorizes no production, upload, publication,
account action, spend, or canonical state mutation.

## 5. Verification

```powershell
python bin/die_company_brain_check.py
python -m pytest bridge/tests -q
git diff --check
```

Regression coverage verifies both principal profiles, source-hash fail-closed
behavior, semantic size and raw-access bounds, snapshot integrity coverage, and
the unchanged Executive/Division-01 MCP tool registries.
