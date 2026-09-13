# DIE-H01 Founder Console Shell v1

Task: H01-141
Status: acceptance candidate

H01-141 promotes the H01-140 presentation seam into a real shadow Founder Console while preserving Mission Control as the global scheduler/lease/authority brain and keeping the existing Factory Console on `127.0.0.1:8876` available until a separate replacement acceptance.

The shell binds loopback `127.0.0.1:20128` by default and exposes exactly nine centralized Founder surfaces: Overview, Production, Providers/BYOK, QC Gallery, Submission Ready, Demand Intelligence, Tasks/Mission Control, System Health and Settings.

All `/api/die/v1/*` surfaces are GET-only. POST/PUT/PATCH/DELETE fail closed. The shell has no direct production, provider-secret, submission, publication, spend or Mission Control mutation authority.

Read-model sources are bounded. Mature Factory Console state is reused by allowlisted loopback GET calls to `8876` for production acceptance/queue, provider inventory, QC gallery and telemetry. Submission Ready is read from `/var/lib/die/h01/submission-ready`. Demand Intelligence reads accepted H01-130/131/132/133 receipts. Tasks/Mission Control reads the canonical Git task graph as a local projection while declaring Mission Control as authority. Providers/BYOK composes browser-native inventory with the H01-142 optional API bridge; browser-native remains primary and API capacity remains supplemental.

The shell fails soft on unavailable read sources and never converts read-model failure into authority. QC image reads are restricted to the legacy QC image endpoint with validated asset IDs and `thumb|full` variants.

Acceptance tests cover the nine GET-only read models, security headers, centralized menu contract, H01-142 provider boundary, local-state readers, legacy QC proxy and shadow-health semantics. Result: 14/14 PASS.

Live shadow canary on 2026-09-13 proved `127.0.0.1:20128/healthz` PASS with `cutover=false`, real Overview/Providers/QC reads, 208 visible QC assets, and simultaneous LISTEN state for both `8876` and `20128`. The canary was then terminated; `20128` closed and `8876` remained LISTEN. No service cutover or legacy restart occurred.
