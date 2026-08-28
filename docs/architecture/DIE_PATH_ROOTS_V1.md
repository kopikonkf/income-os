# DIE Path Roots V1

Date: 2026-08-28
Status: CANON / DIE-102
Contract: `company/contracts/die.path-roots.v1.json`

## Purpose

DIE source, mutable runtime data, MUXIA state, protected configuration, and installed service builds must no longer share an implicit Windows drive root. DIE-102 introduces one OS-neutral path contract while preserving the current Windows deployment until controlled migration/cutover.

## Canonical environment roots

| Variable | Meaning | Windows default | Linux default |
|---|---|---|---|
| `DIE_HOME` | Git-tracked DIE source/canon | `C:\DIE` | `/srv/die` |
| `DIE_STATE_ROOT` | mutable non-MUXIA DIE runtime/data root | `<DIE_HOME>` | `/var/lib/die` |
| `MUXIA_ROOT` | mutable MUXIA profiles/jobs/artifacts/state/logs | `<DIE_STATE_ROOT>\muxia` | `/var/lib/muxia` |
| `DIE_CONFIG_ROOT` | protected host config/secrets | `C:\ProgramData\DIE` | `/etc/die` |
| `DIE_INSTALL_ROOT` | installed/regenerable service runtime | `C:\Program Files\DIE` | `/opt/die` |

Derived paths:

- `STATE = <DIE_STATE_ROOT>/state`
- `WORKSPACES = <DIE_STATE_ROOT>/workspaces`
- `IDENTITY_REGISTRY = <DIE_HOME>/company/identity-registry.json`

All configured roots must be absolute. Relative configured roots fail closed.

## Windows compatibility rule

When only `DIE_HOME` is set on Windows and `DIE_STATE_ROOT` is absent, `DIE_STATE_ROOT` inherits `DIE_HOME`. Therefore the current deployment remains:

```text
DIE_HOME=C:\DIE
STATE=C:\DIE\state
WORKSPACES=C:\DIE\workspaces
```

DIE-102 does not move the live Windows state tree.

## Linux separation rule

With no overrides on Linux:

```text
DIE_HOME=/srv/die
DIE_STATE_ROOT=/var/lib/die
MUXIA_ROOT=/var/lib/muxia
DIE_CONFIG_ROOT=/etc/die
DIE_INSTALL_ROOT=/opt/die
```

This enforces the Chapter #4 source/runtime/config separation without requiring callers to encode Linux literals.

## Runtime-facing refactor

DIE-102 updates the active Python path consumers:

- `bridge/income_os_bridge/config.py`
  - central resolver + canonical constants;
  - `STATE` and `WORKSPACES` derive from `DIE_STATE_ROOT`;
  - source/identity registry derives from `DIE_HOME`;
  - Hermes path gets an environment hook for later DIE-202 while preserving the Windows default.
- `bridge/income_os_bridge/runtime_mcp_server.py`
  - removes operational `PROJECT_ROOT = C:\DIE`;
  - workspace/state boundaries now come from the shared config contract.
- `bin/die_event.py`
  - State Manager writer now uses shared `config.STATE`.
- `bin/die_cron.py`
  - source paths come from `DIE_HOME`;
  - state/workspaces come from `DIE_STATE_ROOT`.
- `bin/die_audit.py`, `die_briefing.py`, `die_heartbeat.py`, `die_summary.py`
  - resolve their sibling `bin` directory from `__file__` rather than pinning `C:\DIE\bin`.
- `bin/m001_loop.py`
  - decisions come from `config.STATE`;
  - governed workspaces come from `config.WORKSPACES`.

Historical documentation, fixtures that deliberately contain Windows examples, and Windows-only PowerShell deployment scripts are not rewritten merely to remove historical path text. Later component migration tasks may replace Windows-only scripts with Linux systemd/service equivalents.

## Hermes boundary

DIE-102 does not migrate Hermes. It only removes an unconditional host-drive dependency:

- optional `DIE_HERMES_HOME` overrides the Hermes runtime root;
- optional `DIE_HERMES_EXE` overrides the executable;
- Windows defaults remain the current AppData/venv location;
- Linux fallback points under `DIE_STATE_ROOT` for later DIE-202 materialization.

No Hermes AppData/profile data is copied by DIE-102.

## Validation

Required gates:

1. Windows fixture preserves current defaults.
2. Linux fixture resolves `/srv/die`, `/var/lib/die`, `/var/lib/muxia`, `/etc/die`, `/opt/die`.
3. Every explicit root override remains independent.
4. Relative configured roots fail closed.
5. Active runtime Python entrypoints do not operationally pin `C:\DIE`.
6. Existing bridge regression remains green.
7. Linux runs the same targeted path tests against the exact implementation commit.
8. No live Windows state/service/profile mutation occurs.

## Migration consequence

DIE-103 can now import components into `/srv/die` without requiring mutable state to live beside source. Later service migration can bind state/config/install roots independently, and CUT-002 can migrate runtime data without turning `/srv/die` into a writable state volume.
