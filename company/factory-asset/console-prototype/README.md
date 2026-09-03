# Factory Console Prototype

Tasks: FA-C004 + FA-C005
Mode: local control-plane prototype; provider dispatch disabled.

Run from the repository root:

```powershell
python company/factory-asset/console-prototype/server.py
```

Then open `http://127.0.0.1:8765/`.

FA-C005 adds a real Blueprint v2 compile preview: the browser sends only the edited Blueprint and UI-only style/consistency/background constraints to the loopback endpoint `/api/compile`. The endpoint invokes the canonical Python `blueprint_compiler.py` and `asset_identity.py`. `/api/batch-intent` creates a bounded local intent from a successful compile preview; it never dispatches a provider job.

No provider credentials, browser profiles, vendor endpoints, marketplace publication actions, or production queue ownership exist in this prototype.
## FA-C006 governed local queue

The Queue view now calls the loopback Factory Core bridge (`/api/queue/jobs`, `/api/queue/submit`, `/api/queue/action`). START/PAUSE/RESUME/CANCEL/RETRY mutate only the local `FactoryJobQueue`; no provider dispatch is implemented. Retry limit and recovery state come from FA-105.
