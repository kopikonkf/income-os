# Executive Worth-Making REVIEW Contract v1

Principal: `chatgpt-plus-executive`
Role: `REVIEWER`
Schema: `die.executive.worth-making-review.v1`
Mode: `READ_ONLY_CHALLENGE`

## Authority

Executive is second-line strategic reviewer. It reviews the exact hash of a Division01-authored Worth-Making artifact and may challenge it; it does not author or edit the Division artifact, does not command Workers, and does not grant production authority.

Every review structurally fixes `division_artifact_edited=false`, `production_authority_granted=false`, the exact Division artifact hash, the exact precheck hash, and Executive principal/snapshot provenance.

## Mandatory challenge domains

All six domains are required exactly once: evidence weakness/contradiction; score inflation/double counting; portfolio overlap/cannibalization; strategic opportunity cost; Product Expression fit; and assumptions that should remain hypotheses. Each challenge cites at least one pinned reference and returns `PASS`, `CONCERN`, `MATERIAL_CONCERN`, or `UNKNOWN`.

## Outcome semantics

- `NO_VETO`: no `MATERIAL_CONCERN` and no `UNKNOWN`. Non-material concerns may remain documented.
- `REVISE`: at least one concern plus explicit required actions. Revision returns to Division01.
- `VETO_PENDING_EVIDENCE`: at least one `UNKNOWN` plus explicit evidence actions.
- `ESCALATE_FOUNDER`: explicit reason for a sovereignty/policy/material strategic question.

Executive never applies requested revisions to the Division artifact itself. OE-004D will define immutable attempt/revision lineage.

## Production boundary

Even `NO_VETO` is not production, spend, account, submission, or publication authority. Founder sovereignty remains downstream and exact-hash scoped.