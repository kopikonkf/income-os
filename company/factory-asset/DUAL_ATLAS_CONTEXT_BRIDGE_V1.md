# Object Atlas x Human Demand Context Bridge v1

Task: `FA-329`

The bridge implements both canonical directions:

- demand-first: `human/problem/industry/intent anchor -> bounded compatible objects -> constrain -> score`
- supply-first: `cleaned object primitive -> bounded compatible human demand contexts -> constrain -> score`

It deliberately does **not** enumerate Object Atlas x Human Atlas. Callers must provide a bounded pre-retrieved candidate set. The bridge scans at most 256 candidates and emits at most 12 results. Exact/partial object-hint coherence, category/class compatibility, use-case overlap and evidence labels contribute to deterministic ranking.

`CANON_EXAMPLE_ONLY` is not demand evidence. A cleaned Object Atlas noun and a Human Atlas context form a hypothesis only; neither side may inherit demand from the other. Output authority is `NONE`: no production, provider dispatch, submission, publication, or spend action follows directly from bridge output.
