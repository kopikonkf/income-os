# Factory Console Prototype

Tasks: FA-C004 + FA-C005
Mode: local control-plane prototype; provider dispatch disabled.

Run from the repository root:

```powershell
python company/factory-asset/console-prototype/server.py
```

Then open the URL printed by the server. The default is `http://127.0.0.1:8876/`; if that port is occupied, the server automatically falls back to another loopback port and prints the actual URL.

FA-C005 adds a real Blueprint v2 compile preview: the browser sends only the edited Blueprint and UI-only style/consistency/background constraints to the loopback endpoint `/api/compile`. The endpoint invokes the canonical Python `blueprint_compiler.py` and `asset_identity.py`. `/api/batch-intent` creates a bounded local intent from a successful compile preview; it never dispatches a provider job.

No provider credentials, browser profiles, vendor endpoints, marketplace publication actions, or production queue ownership exist in this prototype.
## FA-C006 governed local queue

The Queue view now calls the loopback Factory Core bridge (`/api/queue/jobs`, `/api/queue/submit`, `/api/queue/action`). START/PAUSE/RESUME/CANCEL/RETRY mutate only the local `FactoryJobQueue`; no provider dispatch is implemented. Retry limit and recovery state come from FA-105.

## FA-C007 provider dashboard

The Providers view calls `GET /api/providers`, which composes Factory policy evidence, observed-capacity ledger state, deterministic routing rationale and sanitized observability. Current capacity values are explicitly `SYNTHETIC_OBSERVED_FIXTURE`, not live quota polling. Grok remains optional/deferred and cannot block healthy routes.

For a standalone Windows mirror, use `company/factory-asset/bin/sync_console_mirror.py --dest D:\FACTORY_ASSET`; it copies the Console plus required `lib`, `schemas`, `registries` and `fixtures` runtime support tree.

## FA-C009 synthetic end-to-end

The Queue view exposes **Run Synthetic E2E**. It calls `POST /api/synthetic/e2e` and exercises Factory Core policy/capacity routing, lease/queue retry, crash recovery, content-addressed output ingestion and sanitized observability. The run is ephemeral, performs zero live-provider calls and cannot publish/upload.

## FA-C015 live cluster topology

The **Clusters** view calls `GET /api/cluster-topology` and renders sanitized live Cluster A/B broker truth: profile/browser owner identity, tab budget, open pages, active leases/jobs and provider-session readiness/capacity. AUTH_REQUIRED/CHECKPOINT states are rendered as safe operator states without exposing cookies, tokens, OAuth material, profile directories, CDP/control endpoints or lease claim URLs. The view is read-only and does not change the baseline `0 */3 * * *` production cadence or authorize the 100/day scale lane.

## FA-C016 unified operations surface

The **Operations** view calls `GET /api/operations` and joins the current browser-local compiled Blueprint/batch intent with sanitized Factory Core queue, provider-cluster route preview, retries, recovery state, cluster generation-slot pressure and bounded queue controls in one screen. `START`, `PAUSE`, `RESUME`, `CANCEL` and `RETRY` still act only on `FactoryJobQueue`; the selected provider+cluster is explicitly a readiness/capacity preview, not a dispatch commitment. Provider calls, browser-owner actions, secret/session material and marketplace actions remain outside Console authority.
