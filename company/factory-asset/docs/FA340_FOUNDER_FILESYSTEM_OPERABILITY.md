# FA-340 — Founder Filesystem Operability Without Service Ownership Transfer

Status: **DONE / PASS**  
Date: 2026-09-18

FA-340 normalizes Founder read/traverse access across the governed Linux operational roots without turning `kopiko` into the owner of service-managed state.

## Governed roots

- `/var/lib/die`
- `/srv/die`
- `/opt/die`

Founder identity remains `kopiko`, with membership in `die-runtime` and `sudo`.

## Policy

Founder operability is least-privilege:

- operational directories must be readable/traversable;
- operational evidence needed for diagnosis/QC is group-readable through `die-runtime`;
- service owners remain unchanged;
- Founder does not receive group write merely for convenience;
- root-managed repair remains a sudo operation;
- credential/control/session-bearing files remain owner-private where routine Founder read access is unnecessary.

Representative private files retained at `0600` include:

- `/etc/die/hermes/hermes.env`
- Hermes `cron/jobs.json`
- Hermes plugin cache
- Tirith session payloads/log/threat database
- Executive/Division01 browser `Cookies` / `Login Data`

No credential, cookie, token, or private file content was read during FA-340 acceptance.

## Initial live audit

The pre-repair Founder scan found:

- `/srv/die`: zero directory denials, zero unreadable files;
- `/opt/die`: zero directory denials, zero unreadable files;
- `/var/lib/die`: 2 inaccessible directories:
  - `hermes/income-operator/pending_messages`
  - `hermes/.local/state/tirith/sessions`
- 180 unreadable files at the first bounded scan, dominated by:
  - 116 Hermes cron output files,
  - 53 workspace operational artifacts,
  - 7 other Hermes-private/control files,
  - 4 other operational files.

The directory denials were accidental mode drift: both directories were already owned by `die-hermes:die-runtime` but had mode `0700`.

## Implemented boundary

### Runtime directories

The two service-private runtime directories are now `2750 die-hermes:die-runtime`:

- Founder may list/traverse.
- `die-hermes` retains write ownership.
- payload files inside remain `0600`.

Hermes gateway runs `die-founder-fs-runtime-normalize` at both `ExecStartPost` and `ExecStopPost` so restart/shutdown recreation cannot silently restore the Founder denial.

### Operational files

Operational evidence is `0640` and `die-runtime` group-readable, including:

- Factory V1 `postproduction-state.json`;
- raster derivatives and metadata-injected derivatives;
- MUXIA proof jobs/receipts under governed workspaces;
- Hermes per-run cron output;
- Hermes ticker heartbeat / last-success evidence;
- bounded factory canary/acceptance artifacts.

Root-managed rollback scripts remain root-owned but are `0750 root:die-runtime`, allowing Founder inspection/execution under the governed boundary without transferring ownership.

### Persistence in creators

FA-340 changes creators, not only existing bytes:

- postproduction atomic state writes explicitly publish `0640`;
- generated derivative and metadata derivative files are made Founder-readable `0640`;
- Hermes cron output files are published `0640`;
- ticker heartbeat / last-success files are published `0640`;
- pending-message directory creation is patched to `2750` while pending-message payloads remain `0600`;
- gateway start/stop normalizer repairs the two service-private runtime directories.

Hermes cron **control/state files remain owner-private `0600`**.

## Safety

The FA-340 apply tool is allowlist-only and:

- refuses mutation if governed production/browser processes are active;
- snapshots original mode/uid/gid metadata before repair;
- contains no recursive `chmod -R` or `chown -R`;
- never recursively transfers ownership to Founder;
- only changes group to `die-runtime` for explicitly classified operational evidence.

Rollback metadata/source snapshots are under `/var/lib/die/rollback/FA-340/`.

## Live acceptance

Final Founder audit:

```text
directory_denials=0
find_permission_errors=0
operational_unreadable=0
world_writable=0
```

Exactly 10 files remain unreadable by `kopiko`; all are intentional-private classes: Hermes cron control, plugin cache, and Tirith session/log/threat data.

Representative ownership after repair remains:

```text
/var/lib/die                         die-executive:die-runtime 2770
/var/lib/die/hermes                  die-hermes:die-runtime    2770
/var/lib/die/workspaces              root:die-runtime          2770
.../PRODSEED000133                   die-hermes:die-runtime    2770
/srv/die                             kopiko:muxia               0775
/opt/die                             root:root                  0755
```

New post-restart Hermes output and ticker files were observed at `0640 die-hermes:die-runtime`. The latest five cognition cron executions after the gateway changes all completed successfully.

No service ownership, network exposure, provider authority, marketplace submission/publication authority, or spend authority changed.
