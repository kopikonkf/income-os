# COS-004 — Mission Control Constitutional Promotion Acceptance

Date: 2026-09-18  
Task: `COS-004`  
Founder ratification: `RATIFY_COS002_MISSION_CONTROL_CONTROL_PLANE_V1`

## Ratified effect

Mission Control is now the canonical single deterministic operational control/enforcement plane for authorized DIE work.

The promotion preserves all previously Founder-reserved boundaries:

- Founder sovereignty and final authority;
- current autonomy level remains **A0**;
- DIE State Manager remains the sole canonical company operational-state writer;
- `chief-executive-architect-dev` remains Founder-invoked, non-runtime, and non-inheritable;
- `chatgpt-architect` runtime cognition receives no unrestricted DEV authority;
- no autonomous spend/capital allocation;
- no ungated market submission/publication;
- no ungated credential/permission mutation;
- no autonomous new-vendor or irreversible authority;
- ambiguous authority fails closed.

## Canonical changes applied

1. `CONSTITUTION.md`
   - A0-A3 language is actor-neutral and preserves A0.
   - Mission Control replaces Hermes control-plane primacy.
   - State Manager sovereignty is explicit.
   - Architect DEV/runtime separation is explicit.
   - Hermes is retained only as a delegated specialist/compatibility adapter.

2. `COMPANY_BRAIN.md`
   - one-control-plane invariant points to Mission Control;
   - organizational identity and operating loop are updated;
   - M-001 legacy Hermes execution is explicitly subordinate to Mission Control lifecycle authority.

3. `PROTOCOLS/agency-contract-v0.md`
   - runtime invariant names `mission-control`;
   - authority classes and cross-role flow are updated;
   - runtime Architect DEV inheritance is explicitly denied.

4. `company/identity-registry.json`
   - `operational_control_plane = mission-control`;
   - `canonical_state_writer = die-state-manager` is unchanged;
   - `mission-control` is registered with deterministic lifecycle capabilities and `architect_dev_access=deny`;
   - Hermes is demoted to explicitly delegated legacy/edge specialist capabilities.

## Runtime convergence

Generic bridge authority surfaces were updated so the canonical Decision Gateway now routes committed decisions to `mission-control`, and semantic projections report `mission-control` rather than the retired Hermes control-plane identifier. Hermes profile paths remain available only for retained compatibility/runtime-specialist functions.

## Validation

- Company Brain registry validator: **PASS**.
- Control-plane focused bridge tests: **44 PASS / 1 baseline test deselected**.
- The deselected test fails identically on canonical pre-change `main` because of a pre-existing runtime-canon pipeline hash mismatch; it is not a COS-004 regression.
- Company-OS tests: **68 PASS**.
- One-canon validator parity: **9/11 PASS on COS-004 worktree and 9/11 PASS on canonical pre-change `main`**; the same pre-existing `object_snapshot` and `oauth_snapshot` imported-hash mismatches remain outside COS-004 scope.
- No spend, credential mutation, external publication/submission, service stop, or runtime destructive action occurred.

## Result

**PASS.** Founder-ratified constitutional promotion is implemented. Mission Control is the official DIE operational traffic controller; Hermes is no longer the company control plane.