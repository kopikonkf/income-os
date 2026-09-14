# H01-131C Pond5 evidence boundary

H01-131C remains `RUNNING`. These two directories are intentionally separate:

- `controlled-acquired/` is a deterministic smoke proof. It imports the
  checked-in, source-shaped fixture under `controlled-source-shaped/` through
  the H01-131A acquisition core and proves `ACQUIRED`, immutable raw evidence,
  normalized evidence, and a receipt. It is not live marketplace evidence.
- `live-first-party-degraded/` is the real first-party runtime probe against
  `https://contributor.pond5.com/data-trends/illustrations/`. Its receipt is
  retained as `DEGRADED_NO_EVIDENCE`; no robot-challenge response is promoted
  to evidence and no browser cookie, token, credential, or session state is
  read.

The controlled fixture is only a parser/import test document. Its terms and
percentages must not be described as current Pond5 telemetry. The live
acceptance blocker is a compliant acquisition path that can receive the
published Data & Trends document from Pond5 without bypassing the source's
robot challenge or using unauthorized browser state.
