# DIE-H01 Architect graph-width scaling v1

Status: H01-305 implementation subset
Date: 2026-09-12

## Purpose

`graph_width_planner.py` computes a deterministic, dependency-ready
set of engineering tasks that is safe under the coordination snapshot it was
given. It is a read-only preflight, not a scheduler. Mission Control remains
the sole durable task/graph authority and must create the task attempt, lease
the task and perform every durable transition.

## Planning contract

The planner reads a canonical graph observed at `refs/remotes/origin/main` (or
an equivalent already-loaded canonical snapshot). It considers only `READY`
tasks whose declared dependencies are present and canonically `DONE`. Missing
or unknown dependency state is excluded fail closed. A worker branch, local
graph edit, or planner output never unlocks a downstream task.

Eligible tasks are ordered by priority descending and task ID ascending. The
planner then admits tasks until the optional width limit, excluding any task
that collides with an active lease, active mutable-worktree claim, another
selected task's exclusive resource, or another selected task's worktree.
Founder-gated authorities (`FOUNDER`, `FOUNDER_GATED` and
`FOUNDER_REQUIRED`) require exact task authorization in the input snapshot.

Mutable repository writers must declare an unambiguous owner and use the
canonical shared `income-os.repo-write` resource. Thus a shared repo-write
claim can never be silently assigned to two workers. Missing owner or malformed
coordination state is a fail-closed error/exclusion, never a guess.

The output contains selected task IDs, exclusion reasons, graph digest and
canonical ref identity. It explicitly reports `scheduler_action_taken: false`,
`durable_state_mutated: false` and `canonical_graph_mutated: false`. There is
no Mission Control endpoint call, lease acquisition, worktree claim, task
creation or task transition in this helper.

## Existing H01 contract composition

The plan is consumed at the boundary before the H01-300 one-task/one-worker
browser session contract. H01-301 owns browser dispatch, H01-302 owns durable
progress/result completion, and H01-303 owns exact isolated worktrees and
publication coordination. H01-304's separate-resource canary is the evidence
that makes this bounded width preflight eligible. The planner composes these
contracts; it does not replace their lifecycle or create a second scheduler.
