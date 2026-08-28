# DIE-202 ? Hermes + OpenCode Worker-001 Linux Migration V1

Date: 2026-08-28
Status: WAITING_OPERATOR_CREDENTIALS
Final implementation SHA: `c6e26f7a39babb14c12613c30a6d98dd04db493b`

## Scope

DIE-202 materializes Hermes as Linux orchestrator, Worker as a generic bounded executor contract, and OpenCode CLI as Worker-001/default general execution worker V1. It also reconciles the live-only Proactive Operator source into canon and proves the Hermes -> OpenCode -> MUXIA artifact boundary on Linux.

Credential/channel activation is intentionally deferred. No Windows Hermes profile, `.env`, `auth.json`, sessions, `state.db`, caches, provider credentials, or OpenCode provider config are copied.

## Canon

Hermes identity/runtime canon now lives under `company/die-agents/hermes/`. Worker canon lives under `company/workers/`, with `contract/` provider-neutral and `opencode/` as Worker-001.

Role lock:

- Hermes = orchestrator / anti-macet layer.
- Worker = generic bounded executor role.
- Worker-001 = OpenCode CLI.
- MUXIA = browser/provider/profile/job/artifact infrastructure.
- Architect MCP = DEV/control plane, never production worker.

## Proactive Operator reconciliation

Selectively reconciled from live dirty `C:\DIE` after source-only audit and secret scan:

- `bin/die_operator_tick.py`
- `bin/die_operator_switch.py`
- `bin/die_platform_receipt.py`
- `bridge/tests/test_proactive_operator_runtime_v1.py`

The runtime paths were refactored to the DIE-102 path contract. No bulk dirty-tree copy occurred. Final proactive runtime tests: 11/11 PASS.

## OpenCode Worker-001

Linux install root: `/opt/die/workers/opencode`
Mutable home: `/var/lib/die/workers/opencode/home`
Shared workspaces: `/var/lib/die/workspaces`

Pinned package: `opencode-ai@1.18.23`
Functional binary: `1.18.23`

DIE-202 does not invoke `opencode run`; only the actual binary/version probe is used. No provider/model call, credential import, or spend occurs. npm reported a pending package postinstall script under allowScripts policy; no extra approval/script execution was performed merely to suppress that warning.

## Hermes Linux rebuild

Windows baseline was Hermes v0.20.4 on a dirty/grafted local checkout. Linux is rebuilt clean from upstream `https://github.com/NousResearch/hermes-agent.git` at exact commit:

`a0ca7c19204e514f9590ce3b812e029b315ab9e9`

Functional Linux version: Hermes Agent v0.20.5 (2026.8.19).

Install root: `/opt/die/hermes`
Fresh HERMES_HOME: `/var/lib/die/hermes/income-operator`
Protected path binding env: `/etc/die/hermes/hermes.env`, mode 0600 root:root.

Canonical `SOUL.md` and `AGENTS.md` were installed into the fresh runtime and hash-matched against `/srv/die`.

## Gateway fail-closed gate

Systemd unit: `die-hermes-gateway.service`

Current state:

- enabled: no
- active: no
- `/etc/die/hermes/READY`: absent

The unit is READY-gated and therefore cannot accidentally activate before fresh Linux provider/channel credentials are configured. This external operator gate is why DIE-202 remains `WAITING_OPERATOR_CREDENTIALS`.

## Hermes -> OpenCode -> MUXIA proof

The proof was executed first as the migration user and then again as OS identity `die-hermes`.

Flow:

`Hermes worker_dispatch.py -> OpenCode Worker-001 runner -> MUXIA JobRegistry -> ArtifactRegistry -> verified receipt`

Result:

- Hermes accepted worker result: `done`
- OpenCode actual binary: 1.18.23
- MUXIA job final state: `SUCCEEDED`
- synthetic raster SHA256: `431ced6916a2a21a156e38701afe55bbd7f88969fbbfc56d7fe099d47f265460`
- completion evidence: artifact/receipt/hash/bytes/MIME all PASS
- provider call: NO
- consumer ChatGPT: NO
- spend: NO

Shared workspace root is neutral: `/var/lib/die/workspaces`, mode 2770, owner `root:die-runtime`.

## Validation

Final exact implementation SHA `c6e26f7a39babb14c12613c30a6d98dd04db493b`:

- Worker/Hermes/MUXIA targeted tests: 8/8 PASS
- Proactive Operator tests: 11/11 PASS
- full bridge suite: 241/241 PASS
- Windows one-canon: 11/11 PASS
- Linux one-canon: 11/11 PASS
- Windows clean staging: clean
- Linux `/srv/die`: clean

The proactive receipt tests were repaired so subprocess state writes remain in pytest temp roots; the final 241-test suite leaves the staging repo clean without manual state restoration.

## Rollback/control guards

Windows Executive and Division01 Runtime MCP services remain Running/Auto. Windows listeners 8791, 8792, and Division01 Brave/CDP 9333 remain active. Windows Architect MCP 8790 remains active. Live `C:\DIE` remains at `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3`; 38 dirty paths were observed and left untouched. Aether remains external/unmodified.

## DIE-202-R1

Single repair child covers: grafted Hermes provenance discovery; stale canon/test refs; structural OAUTH/Division boundary validation; proactive test isolation; missing `python3.12-venv`; partial venv recovery; upstream-required editable Hermes install; orphaned shallow lock remediation after proving no holder; shared workspace neutral ownership; env permission hardening; and shell transport hygiene. No Windows production credential/profile migration occurred.

## External completion gate

To mark DIE-202 fully DONE later:

1. configure fresh Linux Hermes provider/channel credentials;
2. verify credential scope and sanitized logging;
3. create `/etc/die/hermes/READY`;
4. enable/start `die-hermes-gateway.service`;
5. prove gateway health and operational channel behavior;
6. do not copy Windows auth/profile state to satisfy the gate.

DIE-203 may proceed independently because its task-graph dependency is DIE-104, not DIE-202 credential activation.
