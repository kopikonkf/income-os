# DIE-201 — Division01 Linux Migration V1

Date: 2026-08-28
Status: WAITING_OPERATOR_AUTH
Implementation SHA: `301c794c28f8e5605dc6ca9b061cdaa2312431a9`

## Scope

DIE-201 stages Division01 on Linux without disabling the Windows runtime, cloning browser/auth state, or moving the public endpoint. Principal identity remains `division-head-division01`.

## Canonical identity

Division01 identity moved through Git history from `IDENTITY/division-head-division01.md` to:

`company/division/division001/IDENTITY.md`

Identity registry, component registry, one-canon validator, and runtime-canon tests were updated atomically.

## Linux Runtime Decision MCP

Service: `die-division01-runtime-mcp.service`
Principal: `division-head-division01`
Binding: `127.0.0.1:8792`
Tools: 6

Linux roots:

- source: `/srv/die`
- shared DIE state: `/var/lib/die/state`
- protected config: `/etc/die/division01/runtime-mcp.env`
- install marker: `/opt/die/division01`

The service runs as `die-division01:die-runtime` with systemd hardening equivalent to the Executive lane: `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, private tmp/devices, empty capability set, and localhost-only network policy.

Fresh Linux secrets are generated locally and stored root-owned mode 0600. They are not copied from Windows or printed into canon.

## Shared state boundary

DIE-201 deliberately does not take ownership of `/var/lib/die/state` from the Executive-staged runtime. Existing state ownership remained `die-executive:die-runtime` mode 770, so both principal runtimes use the shared `die-runtime` group boundary.

If state is absent on a fresh host, the Division installer creates it as `root:die-runtime`; it does not assign shared state ownership to the Division service user.

DIE-201 does not perform CUT-002 final state migration.

## Runtime MCP proof

Observed on Linux:

- service active;
- loopback `127.0.0.1:8792` active;
- health principal `division-head-division01`;
- 6 tools exposed;
- unauthenticated MCP returns HTTP 401;
- authenticated initialize PASS;
- authenticated tools/list 6 PASS;
- authenticated `context_snapshot` PASS;
- config file mode 0600 root:root;
- Executive Linux service remained active concurrently.

## OAUTH boundary

`D:\OAUTH` remains a separate next-subproject and is not Division01. DIE-201 imports no OAUTH credential store, provider-specific auth/token/PoW helper, debug/network-capture script, or browser session.

## Consumer ChatGPT policy

The Windows legacy `wake_division01.py` implementation is not the Linux wake contract because it uses private backend/session-token/Sentinel/PoW behavior incompatible with MX-P03.

Linux uses a fresh headed operator profile:

`/var/lib/die/division01/browser-profile`

with launcher:

`company/division/division001/linux/operator_browser.mjs`

Policy:

- manual operator login/recovery;
- no cookie/token/localStorage extraction;
- no private ChatGPT backend calls;
- no protection/PoW bypass;
- no automated prompt submission;
- no output extraction.

Heartbeat:

`/var/lib/die/division01/browser-status.json`

Current state: `AUTH_REQUIRED`.

This is expected negative proof that Windows Brave/CDP session material was not cloned.

## Windows rollback

Windows remains active:

- `DIERuntimeMCPDivision01`: Running / Auto;
- loopback `127.0.0.1:8792`: listening;
- Brave/CDP `127.0.0.1:9333`: listening;
- live `C:\DIE` HEAD remains `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3`.

The live dirty-path count was observed as 38 during DIE-201. This count is not treated as immutable because Windows writers remain active; no reset/discard/fast-forward was performed.

## Validation

- Division01 Linux targeted tests: 6/6 PASS;
- full bridge suite: 222/222 PASS;
- Windows one-canon: 11/11 PASS;
- Linux one-canon: 11/11 PASS;
- Linux Decision MCP health: PASS;
- authenticated MCP read flow: PASS;
- fresh browser profile: AUTH_REQUIRED.

## DIE-201-R1

Single repair child:

- stale runtime-canon test constants updated after identity relocation;
- Division installer corrected not to take ownership of shared `/var/lib/die/state`;
- one partial local patch stopped after changing source but before adding the new test assertion; the guard was completed and retested;
- copied browser heartbeat schema corrected from Executive to Division01;
- several SSH/stat/journal formatting attempts failed before or during read-only evidence collection; they caused no production mutation.

## Completion gate

DIE-201 remains `WAITING_OPERATOR_AUTH` until the Founder/operator manually signs into the Division01 ChatGPT account in the Linux RDP browser and heartbeat becomes `READY`.

No public endpoint cutover occurs in DIE-201.
