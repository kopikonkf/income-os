# DIE-200 — Executive Linux Migration V1

Date: 2026-08-28
Status: WAITING_OPERATOR_AUTH
Runtime implementation SHA: `26a27c1831710d773e7087eab0dd6de06e740c34`

## Scope

DIE-200 rebuilds the Executive runtime on Linux without replacing the Windows production/rollback endpoint. It migrates the Executive identity canon, stages the least-privilege Runtime Decision MCP on Linux, creates a fresh operator-controlled ChatGPT browser profile, and proves Linux runtime isolation/security. ChatGPT MCP connector handoff is first-class `CUT-004A`; the current Windows connector remains rollback-active until that cutover and Windows retirement remains deferred to `CUT-005`.

Architect MCP migration is not part of DIE-200 and remains deferred to `CUT-005 -> MX-053`.

## Source/canon changes

- Executive identity moved through Git history from `IDENTITY/chatgpt-plus-executive.md` to `company/executive/IDENTITY.md`.
- `company/identity-registry.json`, component registry, one-canon validator, and related tests now reference the company-owned identity path.
- Linux service assets are under `company/executive/linux/`.
- Unused Windows-only runtime constants were removed from the shared Runtime MCP server.

## Linux Runtime Decision MCP

Service: `die-executive-runtime-mcp.service`
Principal: `chatgpt-plus-executive`
Binding: `127.0.0.1:8791`

Target roots:

- source: `/srv/die`
- mutable DIE state: `/var/lib/die`
- protected config: `/etc/die/executive/runtime-mcp.env`
- install marker: `/opt/die/executive`

The service runs as dedicated system user `die-executive`, group `die-runtime`, with systemd hardening including `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, private tmp/devices, empty capability bounding set, and localhost-only network policy.

Fresh Linux secrets are generated during install and stored root-owned mode 0600. Secret values are not committed, printed, or copied from Windows.

## Preliminary state bootstrap

`/var/lib/die/state` was bootstrapped from the clean Git-tracked source state only to prove Linux runtime behavior before final cutover. This is **not** `CUT-002` final state sync.

All 15 currently tracked legacy state files matched source-to-Linux SHA-256 during bootstrap proof. Live dirty Windows state was not copied by DIE-200.

## Runtime MCP proof

Observed on Linux:

- service active;
- loopback `8791` active;
- `/health` reports `chatgpt-plus-executive`, server `die-runtime-decision-mcp`, 18 tools;
- unauthenticated `/mcp` request returns HTTP 401;
- authenticated initialize PASS;
- authenticated tools/list returns 18 tools;
- authenticated `system_health` read call PASS;
- state bootstrap hash parity 15/15 PASS;
- journal secret-shape scan 0 hits;
- protected env file mode 0600 root:root.

The Linux instance uses a pre-cutover synthetic HTTPS origin only for OAuth metadata. No public Cloudflare route was moved. Windows Executive service and loopback 8791 remain running as rollback/production reference.

## Consumer ChatGPT browser policy

The Windows legacy wake implementation is **not** ported to Linux. It uses private backend/session-token/Sentinel behavior incompatible with current MX-P03 policy.

Linux uses `company/executive/linux/operator_browser.mjs`:

- standard Google Chrome Stable for human-authenticated profiles, spawned directly rather than through Playwright launch;
- Playwright is used only to attach over loopback CDP for non-sensitive readiness observation;
- browser executable is configurable via `DIE_EXECUTIVE_BROWSER_EXECUTABLE` / `DIE_BROWSER_EXECUTABLE`, default `/usr/bin/google-chrome-stable`;
- dedicated profile `/var/lib/die/executive/browser-profile`;
- profile created fresh on Linux;
- manual operator login/recovery only;
- non-sensitive readiness detection only;
- no cookie/token/localStorage extraction;
- no private ChatGPT backend calls;
- no protective-measure/PoW bypass;
- no automated prompt submission;
- no output extraction.

A non-sensitive heartbeat is written to `/var/lib/die/executive/browser-status.json` with only principal, policy, profile path, observed time, URL/title, composer count, login-UI count, and state.

## Current manual gate

Current browser state:

`AUTH_REQUIRED`

This is expected negative proof for a fresh profile and confirms that Windows session material was not cloned.

DIE-200 must remain `WAITING_OPERATOR_AUTH` until the Founder/operator signs into the Executive ChatGPT account in the already-open Linux RDP browser and the heartbeat becomes `READY`.

No automated login, cookie migration, token extraction, or profile cloning is permitted to satisfy this gate.

## Rollback proof

Windows remains unchanged:

- `DIERuntimeMCPExecutive`: Running / Auto
- Windows loopback `127.0.0.1:8791`: listening
- live `C:\DIE`: `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3`, 37 dirty paths preserved

No Windows service/task was stopped or disabled.

## Validation

- Executive Linux targeted tests: 6/6 PASS
- full Windows bridge suite: 216/216 PASS
- one-canon validator: 11/11 PASS
- Linux exact-source one-canon: 11/11 PASS
- Linux service health: PASS
- fresh-profile browser proof: AUTH_REQUIRED (expected pending manual login)

## DIE-200-R1

One repair child is in use for tooling/deployment hygiene and canon correction during this atomic task. It includes shell-transport quoting/CRLF issues, shell-safe EnvironmentFile quoting, hardened login-state detection, relocation of Executive identity references, and test constants updated after the canonical identity move. None of these repairs copied credentials or mutated the Windows production runtime.

## Completion gate

DIE-200 can become `DONE` only when:

1. browser heartbeat is `READY` after manual Linux login;
2. exact final main is clean on Windows staging and Linux;
3. Decision MCP remains healthy and loopback-only;
4. Windows rollback Executive remains active;
5. no public endpoint cutover has occurred;
6. final receipt and task graph are updated.
