# LASTSTANDINGPOINT.md

Date: 2026-08-23
Project: Digital Income Empire — Company Holdings
Mode: Chief Executive Architect
Workflow stage: M-001 RECONCILIATION PASS / WAKE LIVE / SECURITY CANON VERIFIED
Canonical runtime: C:\DIE
Canonical repository: https://github.com/kopikonkf/income-os
Working branch: architect/wake-security-canon-v1
Base branch: main
Base/merge commit: acb4109e7977b3deda31f3d428b94fb0e6ee724b
Phase A implementation commit: ae2a42aee309b9eee05dbf4376ef86806c967c4d
Phase B1 implementation commit: 2e46e43e99a6aff9c4390c3f70e1e5471d9b28b0
Phase B2A initial implementation commit: ba05dcf8f3e54092f8f92c8de488f3e0702bfce6
Phase B2B1 implementation commit: ff6f850eb0c35a15fb62f727c69ac45cf05767d5
Merged PRs: https://github.com/kopikonkf/income-os/pull/8, https://github.com/kopikonkf/income-os/pull/9, https://github.com/kopikonkf/income-os/pull/10, and https://github.com/kopikonkf/income-os/pull/11
Draft PR: https://github.com/kopikonkf/income-os/pull/21
Publication status: VERIFIED / DRAFT PR #21 OPEN

## Verified merge baseline

PR #7 — Executive MCP Activation Gate v1.1 is merged and closed:

https://github.com/kopikonkf/income-os/pull/7

- merged at: 2026-08-21T07:53:37Z;
- PR head: 4199f78114df531e0162748ced576dc482063419;
- merge commit: 9cfe7ff781726a887e8ce039fd7f6bde0f79b019;
- C:\DIE\main and origin/main were synchronized before the Phase A branch;
- post-merge Company Brain validator: PASS;
- post-merge regression before Phase A: 69 passed.

PR #8 — Executive MCP Activation Phase A v1 is merged and closed:

https://github.com/kopikonkf/income-os/pull/8

- merged at: 2026-08-21T11:54:04Z;
- feature head: 16b8cdb12e6c94ae85cd6c5ce10b2e40102b26fa;
- merge commit: c585f9d2fd3016b84f59ebc629ba339e4dc2a719;
- C:\DIE\main and origin/main are synchronized at the merge commit;
- post-merge full bridge regression: 76 passed;
- post-merge Phase A installed-state preflight: PASS / ready=true;
- live runtime state changes survived synchronization.

## Canonical runtime boundary

~~~text
GitHub main
  = canonical code + governed documents

C:\DIE\state
  = live append-only state + generated runtime projections

C:\ProgramData\DIE\ExecutiveMCP
  = local non-secret Executive MCP activation runtime
~~~

Runtime-owned repository paths currently preserved and excluded:

- state/EVENTS.jsonl — modified;
- state/projection/.cursor — modified;
- state/projection/BRIEFING.md — modified;
- state/projection/EVENTS.jsonl — modified;
- state/projection/WAKE.flag — currently absent/deleted by runtime;
- state/organism-test/groundtruth-20260821.txt — untracked runtime/test ground truth;
- state/DECISIONS.jsonl — unmodified.

These paths must not be staged, discarded, restored, rewritten, or included in
an architecture PR without a separate state-governance decision.

## Corrected P0–P9 standing

| Stage | Actual status | Canonical standing |
| --- | --- | --- |
| P0 — Autopsy/Salvage | COMPLETE | KEEP/MODIFY/RETIRE and salvage boundary complete. |
| P1 — Company Brain | COMPLETE | Constitution, identities, registry, agency contract, and validator merged in PR #2. |
| P2 — Architect MCP | FUNCTIONALLY COMPLETE | Live C:\DIE inspection/write/test/Git cycle works; security-hardening debt remains. |
| P3 — Plus Line 1/2 | CUSTOM MCP P0/P1 CANONICAL; P2 TUNNEL DEFERRED | `income_os_bridge` is the canonical local CLI/stdio Decision Fabric. Executive tunnel-client is optional P2, gated until after PECAH TELOR and separate Founder authorization. |
| P4 — Division Line 1/2 | TEMPLATE FOUNDATION ONLY | Keep inactive until one real division and scoped projection exist. |
| P5 — State Layer | COMPLETE v1 | Signed bounded snapshots, typed evidence, replay-safe commit, and State Manager boundary merged in PR #3. |
| P6 — Decision Gateway | COMPLETE v1 | Stateless validation/router and Hermes-ready route merged in PR #4. |
| P7 — Hermes/Worker/Proxima | PARTIAL EXISTING | Hermes income-operator is the operational control plane; P0/P1 mission proof is next. Proxima remains Worker ↔ Web Chat AI only. |
| P8 — Dashboard | BLOCKED BY DESIGN | Start only after one real division and one economic loop are alive. |
| P9 — Genome/Bootstrap/etc. | DEFERRED | Classify after the current decision/execution loop is operational. |

## Phase A authorization executed

Founder authorized Executive MCP Activation Phase A bootstrap only, with these
hard boundaries:

- versioned Windows scripts, runbook, and tests;
- latest official tunnel-client download and fixed-path installation;
- non-secret runtime/config/log directories with restrictive ACLs;
- dry-run, tests, and unauthenticated outbound/local preflight;
- no secrets, credentials, tunnel IDs, profile initialization, tunnel mutation,
  MCP start/deploy/exposure/registration, Windows service, or scheduled task;
- no commit, push, or PR without separate publication authorization.

All boundaries were preserved.

## Versioned Phase A implementation

Merged through PR #8 from architect/executive-mcp-activation-v1:

- ops/windows/executive-mcp/Install-DIEExecutiveMcpPhaseA.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpPhaseA.ps1
- docs/operations/EXECUTIVE_MCP_ACTIVATION_PHASE_A_V1.md
- bridge/tests/test_executive_activation_bootstrap_v1.py
- LASTSTANDINGPOINT.md — updated canonical handoff

Installer properties:

- default mode is Plan;
- Apply uses the fixed root C:\ProgramData\DIE\ExecutiveMCP only;
- release discovery is restricted to the official openai/tunnel-client GitHub
  release API and official release URLs;
- archive SHA-256 must match official SHA256SUMS.txt;
- reported version must match the release tag;
- tunnel-client help quickstart must succeed;
- only the verified executable and non-secret install manifest persist;
- transient bootstrap files are removed;
- no activation command exists in the Phase A scripts.

## Installed Phase A runtime

Official source:

- repository: https://github.com/openai/tunnel-client
- release: v0.0.12
- release URL: https://github.com/openai/tunnel-client/releases/tag/v0.0.12
- asset: tunnel-client-v0.0.12-windows-amd64.zip
- published: 2026-08-20T05:04:29Z

Installation:

- root: C:\ProgramData\DIE\ExecutiveMCP
- binary: C:\ProgramData\DIE\ExecutiveMCP\bin\tunnel-client.exe
- evidence manifest:
  C:\ProgramData\DIE\ExecutiveMCP\bin\tunnel-client.install.json
- config directory: empty;
- logs directory: empty;
- runtime directory: empty after bootstrap cleanup;
- ACL inheritance: disabled on root, bin, config, logs, and runtime;
- ACL principals: Local System, built-in Administrators, invoking Windows
  identity.

Verification evidence:

- official/downloaded archive SHA-256:
  2a2804933924e38a502d62b61f0266cb80d56d65744f4c29876b2bf9c1544356
- installed binary SHA-256:
  6649169733686805ca16cccd91774594d0c017fd729c37ad4ce1cd18323d9ae8
- reported version:
  0.0.12+881c9a8fed7cccbe6607cd419863bbca506b8215
- version/release match: PASS;
- help quickstart exit code: 0;
- help-output digest recorded in the non-secret install manifest;
- Authenticode observation: NotSigned;
- trust basis used: exact official GitHub release URL + official checksum manifest
  + matching version + successful quickstart help.

## Verification result

Dry-run:

~~~text
schema=die.executive.mcp.activation.phase-a.v1
mode=Plan
release=v0.0.12
writes_performed=false
all safety flags=false
~~~

Pre-install preflight:

~~~text
ready=true
Windows AMD64=true
Line 1 bootstrap present=true
Line 2 bootstrap present=true
Python present=true
tunnel-client process absent=true
api.openai.com:443 reachable=true
~~~

Repository regression:

~~~text
Phase A targeted tests: 7 passed
Full bridge regression: 76 passed
git diff --check: PASS
~~~

Installed-state preflight:

~~~text
schema=die.executive.mcp.activation.phase-a.preflight.v1
mode=Installed
ready=true
failed_checks=[]
fixed directories present=true
all directory ACL checks=true
binary hash matches manifest=true
version matches release=true
quickstart help matches manifest=true
bootstrap workspace clean=true
tunnel-client process absent=true
api.openai.com:443 reachable=true
~~~

Post-bootstrap negative proof:

- tunnel profiles initialized: FALSE;
- OpenAI tunnels created or modified: FALSE;
- credentials requested or read: FALSE;
- MCP services started/deployed/exposed/registered: FALSE;
- Windows service created: FALSE;
- scheduled task created: FALSE;
- related tunnel-client process running: FALSE;
- temporary release archive/checksum/extraction artifacts retained: FALSE.

## Activation standing

The fail-closed activation checker was intentionally not rerun because Phase A
must not inspect runtime secret prerequisites.

Current canonical fact:

- tunnel-client binary is physically installed and verified at the fixed path;
- it is not added to PATH and not configured as an activation environment value;
- no runtime Platform API key or HMAC material was requested, read, generated, or
  provisioned;
- no Line 1 or Line 2 tunnel ID was requested, read, stored, or initialized;
- no profile, doctor run, tunnel process, MCP process, ChatGPT registration, or
  tool call was performed.

Therefore P3 runtime activation remains blocked by design.

## Published Phase A manifest

Exact repository files merged through PR #8:

- LASTSTANDINGPOINT.md
- bridge/tests/test_executive_activation_bootstrap_v1.py
- docs/operations/EXECUTIVE_MCP_ACTIVATION_PHASE_A_V1.md
- ops/windows/executive-mcp/Install-DIEExecutiveMcpPhaseA.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpPhaseA.ps1

Explicit publication exclusions:

- state/EVENTS.jsonl
- state/DECISIONS.jsonl
- all state/projection artifacts
- all state/organism-test artifacts
- C:\ProgramData runtime installation and evidence manifest
- secrets, credentials, tunnel IDs
- temporary files and cache artifacts

Implementation commit ae2a42aee309b9eee05dbf4376ef86806c967c4d was merged through
PR #8 at c585f9d2fd3016b84f59ebc629ba339e4dc2a719. No runtime state
path or excluded artifact was staged or committed.

## Phase B1 recommended boundary

Official OpenAI documentation confirms that real activation requires a tunnel_id,
a runtime API key, a reachable private MCP server, the correct organization and
workspace association, profile initialization, doctor validation, then a running
tunnel-client before ChatGPT discovery.

Canonical reference:

https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

Installed tunnel-client v0.0.12 help also confirms that the control-plane key can
be referenced through an environment variable or an ACL-protected file. Phase B1
will build only the reusable secure-config tooling and lane wrappers. It will not
receive, create, store, or validate any real secret or tunnel ID.

Phase B1 code-only target:

- plan-first Windows secure-config bootstrap;
- fixed ProgramData secret/config path contract with restrictive ACL rules;
- separate Line 1 and Line 2 wrapper contracts;
- file-reference support for the tunnel runtime key;
- process-scoped HMAC injection contract for Line 2 only;
- redaction, zero-secret-output, and no-environment-dump tests;
- dry-run and static validation only;
- no profile initialization, doctor, run, service, scheduled task, deployment,
  exposure, or ChatGPT registration.

## Phase B1 authorization executed

~~~text
AUTHORIZED: execute Executive MCP Activation Phase B1 secure-config tooling only.
Implement versioned Windows secure-config and isolated lane wrapper scripts,
runbook, and tests on architect/executive-mcp-secure-config-v1.
Use only fixed C:\ProgramData\DIE\ExecutiveMCP paths, restrictive ACL contracts,
and file-based secret references supported by the installed tunnel-client.
Run dry-run validation and repository tests only.

Exclude state/EVENTS.jsonl, state/DECISIONS.jsonl,
all state/projection and state/organism-test runtime artifacts,
the C:\ProgramData runtime installation, all real secrets, credentials,
tunnel IDs, temporary files, and cache artifacts.
Do not request, read, generate, or provision any real API key or HMAC material.
Do not create or modify any OpenAI tunnel.
Do not initialize tunnel profiles.
Do not run tunnel-client doctor or tunnel-client run.
Do not start, deploy, expose, or register either MCP service.
Do not create a Windows service or scheduled task.
Do not commit, push, or create a PR until separate publication authorization.
~~~

Phase B1 tooling is verified, committed, pushed, and published in draft PR #9.
B2 still requires the Founder to enter two tunnel IDs and runtime secret material
locally on the VPS through an interactive no-echo channel after separate B2
authorization. No secret or tunnel ID may be pasted into chat or committed to Git.

## Phase B1 implementation and verification

Implemented locally on `architect/executive-mcp-secure-config-v1`:

- `ops/windows/executive-mcp/New-DIEExecutiveMcpSecureConfigPlan.ps1`
- `ops/windows/executive-mcp/Invoke-DIEExecutiveLine1Tunnel.ps1`
- `ops/windows/executive-mcp/Invoke-DIEExecutiveLine2Tunnel.ps1`
- `ops/windows/executive-mcp/Test-DIEExecutiveMcpSecureConfig.ps1`
- `docs/operations/EXECUTIVE_MCP_SECURE_CONFIG_V1.md`
- `bridge/tests/test_executive_secure_config_v1.py`
- `LASTSTANDINGPOINT.md`

Implemented contracts:

- plan-only secure-config compiler with no Apply mode and no ProgramData access;
- fixed, lane-separated config, secret, log, PID, health, and profile paths;
- lane-specific control-plane key references using the installed client's
  `file:C:\ProgramData\...` syntax;
- protected ACL contract limited to Local System, built-in Administrators, and
  the future local activation operator;
- Line 1 strips inherited HMAC and fallback API-key variables without reading
  them;
- Line 2 validates protected files, injects HMAC material process-locally only in
  a future separately authorized Run, and clears it in `finally`;
- both wrappers default to Plan and bind health/admin endpoints to distinct
  loopback addresses;
- remote admin UI, raw HTTP logging, environment enumeration, detached process,
  Windows service, and scheduled-task paths are absent.

Verification:

~~~text
Secure-config dry-run: PASS
Checks: 29/29
Failed checks: none
ProgramData accessed by validation: false
Secret values returned: false
Targeted Phase B1 tests: 9 passed
Full bridge regression: 85 passed
git diff --check: PASS
Staged paths: 0
~~~

Negative proof:

- no real API key, HMAC value, key ID, or tunnel ID was requested, read,
  generated, provisioned, or printed;
- no ProgramData directory, profile, or secret file was created or modified;
- no tunnel profile was initialized;
- no tunnel-client doctor or run command was executed;
- no MCP service, tunnel, Windows service, scheduled task, deployment, exposure,
  or ChatGPT registration was created;
- implementation commit 2e46e43e99a6aff9c4390c3f70e1e5471d9b28b0 was pushed to the feature branch;
- draft PR #9 was created against main; no merge or Phase B2 action was performed;
- all runtime-owned state/projection/organism-test paths remain excluded and
  untouched by the architecture work.

Exact published Phase B1 manifest:

- LASTSTANDINGPOINT.md
- bridge/tests/test_executive_secure_config_v1.py
- docs/operations/EXECUTIVE_MCP_SECURE_CONFIG_V1.md
- ops/windows/executive-mcp/Invoke-DIEExecutiveLine1Tunnel.ps1
- ops/windows/executive-mcp/Invoke-DIEExecutiveLine2Tunnel.ps1
- ops/windows/executive-mcp/New-DIEExecutiveMcpSecureConfigPlan.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpSecureConfig.ps1

## Phase B1 publication standing

Draft PR #9 is open:

https://github.com/kopikonkf/income-os/pull/9

- title: feat: Executive MCP secure config tooling v1;
- state: MERGED / CLOSED;
- base: main;
- head: architect/executive-mcp-secure-config-v1;
- initial implementation commit:
  2e46e43e99a6aff9c4390c3f70e1e5471d9b28b0;
- exact publication manifest: the seven Phase B1 paths listed above;
- runtime-owned state/projection/organism-test paths: excluded;
- ProgramData runtime, credentials, secret values, HMAC material, and tunnel IDs:
  excluded;
- Phase B2A: subsequently executed locally on its dedicated feature branch; publication remains pending.

The GitHub connector could read repository state but returned HTTP 403 for PR
creation. The already-configured VPS `gh` authentication created the authorized
draft PR successfully. No scope was expanded.

## PR #9 post-merge verification

Canonical parity:

~~~text
C:\DIE\main = 36ffd8fe5fce05c4c51e7b712c69d0f883d76746
origin/main = 36ffd8fe5fce05c4c51e7b712c69d0f883d76746
PR #9 merge = 36ffd8fe5fce05c4c51e7b712c69d0f883d76746
~~~

Verification:

- Phase B1 secure-config dry-run: PASS / ready=true / 29 of 29 checks;
- full bridge regression: 85 passed;
- PR #9 merged diff: exactly the seven authorized Phase B1 paths;
- staged paths: zero;
- runtime-owned state/projection/organism-test changes survived the fast-forward
  and remain excluded;
- no ProgramData mutation, secret access, profile initialization, tunnel-client
  doctor/run, MCP start, external tunnel mutation, or registration occurred.

## Phase B2 decomposition

Phase B2 is divided to avoid combining filesystem security, secret handling,
tunnel identity, process startup, and external registration in one blast radius.

- B2A - non-secret runtime skeleton: create only fixed lane directories and
  restrictive ACLs; no secret files or profiles.
- B2B - local secret and tunnel-identity provisioning: Founder-operated,
  no-echo, VPS-side only.
- B2C - profile initialization and doctor validation: no persistent run.
- B2D - controlled Line 1 activation and ChatGPT registration.
- B2E - controlled Line 2 activation only after Line 1 proves healthy.

## Phase B2A authorization executed

Founder authorization was interpreted as the next bounded activation step:
Phase B2A non-secret runtime skeleton only. The blast radius remained limited to
empty fixed-path directories and ACL metadata.

Implemented locally on architect/executive-mcp-secure-runtime-v1:

- ops/windows/executive-mcp/Initialize-DIEExecutiveMcpSecureRuntime.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpSecureRuntime.ps1
- docs/operations/EXECUTIVE_MCP_SECURE_RUNTIME_V1.md
- bridge/tests/test_executive_secure_runtime_v1.py
- LASTSTANDINGPOINT.md

Applied ProgramData topology:

~~~text
C:\ProgramData\DIE\ExecutiveMCP
  config\line1
  config\line2
  secrets\line1
  secrets\line2
  logs\line1
  logs\line2
  runtime\line1
  runtime\line2
~~~

The shared secrets root and all eight lane directories have protected ACLs.
Only Local System, built-in Administrators, and the current activation operator
SID are permitted explicit Allow FullControl rules. Inheritance is disabled.

## Phase B2A verification

Pre-Apply:

~~~text
Initializer Plan: PASS
Verifier Plan: PASS
writes_performed=false
all secret/profile/tunnel/process/service/task/external-mutation flags=false
Targeted tests: 8 passed
Full bridge regression: 93 passed
~~~

Apply and Installed verification:

~~~text
First Apply: 9 directories created and protected
Installed ready: true
Installed checks: 36 of 36 passed
Failed checks: none
Managed file count: 0
Tunnel-client process absent: true
Secret values read: false
Profile contents read: false
~~~

Idempotency proof while all lanes remained empty:

~~~text
Second Apply created directories: 0
Second Apply existing directories: 9
ACL restricted: true
Installed ready after second Apply: true
~~~

Post-Apply regression:

~~~text
Targeted tests: 8 passed
Full bridge regression: 93 passed
git diff --check: PASS
Staged paths: 0
~~~

Phase A binary integrity remained unchanged:

~~~text
tunnel-client.exe SHA-256:
6649169733686805ca16cccd91774594d0c017fd729c37ad4ce1cd18323d9ae8
~~~

Negative proof:

- no secret, profile, configuration, log, or PID file was created;
- no real credential, API key, HMAC value, key ID, or tunnel identity was
  requested, read, generated, provisioned, validated, or printed;
- no tunnel profile was initialized;
- tunnel-client doctor and tunnel-client run were not invoked;
- no MCP process, Windows service, scheduled task, OpenAI tunnel mutation,
  deployment, exposure, or ChatGPT registration occurred;
- the Phase A binary and installation evidence were not modified;
- repository runtime-owned state/projection/organism-test paths remain excluded
  and untouched by the architecture work;
- before publication, staged paths were zero; publication is restricted to the exact five-file B2A manifest.

B2A Apply is no longer safe after B2B adds any lane artifact; its fail-closed
empty-directory checks intentionally prevent that reuse.

## Exact Phase B2A publication manifest

- LASTSTANDINGPOINT.md
- bridge/tests/test_executive_secure_runtime_v1.py
- docs/operations/EXECUTIVE_MCP_SECURE_RUNTIME_V1.md
- ops/windows/executive-mcp/Initialize-DIEExecutiveMcpSecureRuntime.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpSecureRuntime.ps1

Explicit publication exclusions:

- state/EVENTS.jsonl
- state/DECISIONS.jsonl
- every state/projection runtime artifact
- every state/organism-test runtime artifact
- the complete C:\ProgramData runtime installation
- secrets, credentials, secret files, profile files, tunnel IDs
- temporary files and cache artifacts

## PR #10 post-merge verification

PR #10 is merged and closed:

https://github.com/kopikonkf/income-os/pull/10

- merged at: 2026-08-21T13:11:36Z;
- feature head: 9e11ca8de8bb8954c5bc0767043e305c572b5e98;
- merge commit: b88b2f17415301f43819cd675bbe1397d75c18da;
- merged diff: exactly the five authorized B2A paths;
- C:\DIE\main and origin/main are synchronized at the merge commit;
- runtime state diff fingerprint and organism ground-truth hash were identical
  before and after fast-forward;
- staged paths: zero.

Post-merge verification:

~~~text
B1 secure-config: ready=true / 29 of 29 checks
B2A Installed: ready=true / 36 of 36 checks
B2A targeted tests: 8 passed
Full bridge regression: 93 passed
Managed runtime file count: 0
Tunnel-client process absent: true
tunnel-client.exe SHA-256 unchanged:
6649169733686805ca16cccd91774594d0c017fd729c37ad4ce1cd18323d9ae8
~~~

## Phase B2B refinement

The former B2B boundary is split to keep code review separate from real secret
handling:

- B2B1 — repository-only no-echo secret-provisioning tooling;
- B2B2 — Founder-operated local provisioning and metadata-only verification;
- B2C — two-lane tunnel identity/profile initialization and doctor validation;
- B2D — controlled Line 1 activation and ChatGPT registration;
- B2E — controlled Line 2 activation after healthy Line 1 evidence.

Tunnel identities belong to B2C, not B2B1/B2B2. No tunnel identity is accepted
or stored by the secret-provisioning tooling.

## Phase B2B1 implementation

Implemented locally on architect/executive-mcp-secret-provisioning-v1:

- ops/windows/executive-mcp/Set-DIEExecutiveMcpSecrets.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpSecrets.ps1
- docs/operations/EXECUTIVE_MCP_SECRET_PROVISIONING_V1.md
- bridge/tests/test_executive_secret_provisioning_v1.py
- LASTSTANDINGPOINT.md

Contracts implemented:

- Plan-first provisioning and validator scripts;
- fixed create-only Line 1 and Line 2 secret-file paths;
- explicit Provision mode plus ConfirmInteractiveProvisioning gate;
- directly attached interactive console requirement;
- two-entry Read-Host -AsSecureString confirmation;
- no plaintext command-line or environment input;
- unmanaged BSTR handling without plaintext managed-string conversion;
- byte/character buffer clearing and ZeroFreeBSTR cleanup;
- Line 2 HMAC minimum 32-byte contract and strict ASCII key-id contract;
- exact protected ACL principal and FullControl validation;
- FileMode.CreateNew and FileShare.None writes;
- transaction-scoped rollback of only newly created files;
- refusal to overwrite or rotate existing files;
- refusal to operate on non-empty lanes or while tunnel-client is running;
- metadata-only Installed validator that never opens a secret file;
- structural prohibition of Line 1 HMAC material;
- tunnel identity and profile initialization deferred to B2C.

## Phase B2B1 verification

~~~text
PowerShell syntax errors: 0
Provisioner Plan: PASS
Validator Plan: PASS
ProgramData accessed by Plan: false
Prompts displayed: false
Writes performed: false
Secret values read: false
Tunnel identities requested or read: false
Targeted B2B1 tests: 9 passed
Full bridge regression: 102 passed
Managed runtime files before tests: 0
Managed runtime files after tests: 0
Tunnel-client process absent: true
Staged paths: 0
~~~

Negative proof:

- Provision mode was not invoked;
- Installed mode was not invoked;
- no real API key, HMAC material, key ID, or tunnel identity was requested,
  read, generated, provisioned, validated, printed, hashed, or stored;
- no ProgramData file, profile, log, PID, or evidence artifact was created;
- no tunnel profile, doctor, run, MCP process, Windows service, scheduled task,
  OpenAI tunnel mutation, deployment, exposure, or registration occurred;
- live state, projection, and organism-test artifacts remain excluded and
  untouched by B2B1 architecture work;
- before publication, no repository path was staged; publication is restricted to the exact five-file B2B1 manifest.

## Exact B2B1 publication manifest

- LASTSTANDINGPOINT.md
- bridge/tests/test_executive_secret_provisioning_v1.py
- docs/operations/EXECUTIVE_MCP_SECRET_PROVISIONING_V1.md
- ops/windows/executive-mcp/Set-DIEExecutiveMcpSecrets.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpSecrets.ps1

Explicit exclusions:

- state/EVENTS.jsonl and state/DECISIONS.jsonl;
- all state/projection and state/organism-test runtime artifacts;
- the complete C:\ProgramData runtime installation;
- every real secret, credential, HMAC value, key ID, and tunnel identity;
- profile, configuration, log, PID, temporary, and cache artifacts.

## PR #11 post-merge verification

PR #11 is merged and closed:

https://github.com/kopikonkf/income-os/pull/11

- merged at: 2026-08-21T13:46:07Z;
- feature head: ff6f850eb0c35a15fb62f727c69ac45cf05767d5;
- merge commit: 5f622d70faa1fa19265fe1d33ff567ac4215f885;
- merged diff: exactly the five authorized B2B1 paths;
- C:\DIE\main and origin/main are synchronized at the merge commit;
- live runtime diff fingerprint and organism ground-truth hash were identical
  before and after fast-forward;
- staged paths: zero.

Post-merge verification executed only Plan and repository tests:

~~~text
Provisioner schema: die.executive.mcp.secret-provisioning.v1
Provisioner mode: Plan
Validator schema: die.executive.mcp.secret-provisioning.preflight.v1
Validator mode: Plan
ProgramData accessed: false
Prompts displayed: false
Writes performed: false
Secret values read: false
Tunnel identities requested or read: false
B2B1 targeted tests: 9 passed
Full bridge regression: 102 passed
git diff --check: PASS
~~~

Negative proof:

- Provision mode was not invoked;
- B2B1 Installed mode was not invoked;
- no ProgramData path or secret metadata was inspected;
- no real API key, HMAC material, key ID, or tunnel identity was requested,
  read, generated, provisioned, validated, printed, hashed, or stored;
- no tunnel profile, doctor, run, MCP process, Windows service, scheduled task,
  OpenAI tunnel mutation, deployment, exposure, or registration occurred;
- all live state/projection/organism-test paths remain preserved and excluded.

## Founder decision — Executive tunnel deferred

Founder exercised sovereign authority under CONSTITUTION.md sections 1.3, 1.4,
and 3.1:

- Executive MCP tunnel activation B2B2/B2C is deferred indefinitely;
- no OpenAI billing top-up or control-plane key will be created for foundation
  connectivity;
- no control-plane API key, HMAC material, key ID, tunnel identity, profile
  initialization, doctor, or tunnel run may be requested, stored, or validated
  until separately re-authorized after PECAH TELOR;
- the B2A ACL-protected C:\ProgramData\DIE\ExecutiveMCP skeleton remains intact
  and empty;
- tunnel-client is classified as optional Transport P2, not a foundation
  dependency.

Founder/OpenCode reported that B2B2 Provision was invoked once and cancelled with
Ctrl+C at the first no-echo prompt. No input was submitted, no secret file was
created, no file was written, and the transaction rolled back. Architect accepts
this as operator evidence and will not inspect secret paths.

## Canonical Decision Fabric boundary

- P0: local projections and read-only CLI surfaces, including recent_events,
  system_health, and state/projection/BRIEFING.md;
- P1: local stdio MCP and hermes_state_reader, using the income-operator profile
  state database read-only;
- operational control plane: hermes-operator/income-operator;
- canonical physical writer: die-state-manager;
- P2: optional loopback/network transport only after PECAH TELOR and explicit
  Founder authorization.

P0/P1 must evolve as the DIE Decision Fabric. P2 may not replace it and may not
become a billing dependency for foundation operation.

## Custom MCP Decision Fabric v1 implementation

Implemented locally on architect/custom-mcp-decision-fabric-v1:

- bridge/income_os_bridge/config.py
- bridge/income_os_bridge/envelope.py
- bridge/income_os_bridge/mcp_server.py
- bridge/income_os_bridge/projection.py
- bridge/tests/test_decision_fabric_p0_p1_v1.py
- bridge/tests/test_executive_activation_readiness_v1.py
- LASTSTANDINGPOINT.md

Authority contract now declared on semantic P0/P1 responses:

~~~text
operational_control_plane: hermes-operator/income-operator
canonical_writer: die-state-manager
~~~

The stdio server remains named income-os-bridge, version 0.5.0, and is explicitly
the canonical local Decision Fabric P0/P1. P2 network transport is optional and
Founder-gated.

## SOUL and AGENTS synchronization standing

Founder/OpenCode completed the trusted local synchronization that ChatGPT
Architect correctly refused because the Hermes profile is outside configured
write roots.

SOUL:

~~~text
source: C:\DIE\IDENTITY\hermes-operator\SOUL.md
target: C:\Users\aethers\AppData\Local\hermes\profiles\income-operator\SOUL.md
SHA-256: 7015C2C28F0C4D7AC94E5CF667899D34489349FA5A5661B9524AAEF0E5592BA7
result: source/target identical
~~~

AGENTS:

~~~text
source: C:\DIE\AGENTS.md
target: C:\Users\aethers\AppData\Local\hermes\profiles\income-operator\AGENTS.md
SHA-256 prefix: 14AE57417A5725B88049A4C8CA1ABB433F303A85EA6
result: source/target identical
~~~

Post-sync `hermes doctor`: PASS. No restart was required. The identity sync gap
is closed; Architect did not bypass its deny-by-default root boundary.

## P0 Organism baseline result

Executed through local P0 surfaces only:

~~~text
system_health: completeness=complete, source_trust=VERIFIED
gateway_running=true
operational_control_plane=hermes-operator/income-operator
canonical_writer=die-state-manager
recent_events: source_trust=VERIFIED, bounded/truncated as designed
briefing_get: authority contract present
ground truth Kanban: no matching tasks
BRIEFING Kanban claim: empty
truth-versus-projection drift for Kanban claim: 0
event last seq: 342
BRIEFING last seq: 307
scheduled catch-up backlog: 35
Decision Fabric targeted tests: 7 passed
Full bridge regression: 109 passed
Conformance: PASS, 109 passed / 0 failed
git diff --check: PASS
~~~

Runtime conformance evidence:

~~~text
state/organism-test/conformance-p0-decision-fabric-20260821.json
~~~

This file is runtime evidence and must remain unstaged.

The P0 foundation baseline passes. The full Organism Test business gate does not
yet pass because there is no active mission, proposal decision, artifact shipment,
buyer contact, or verified revenue. Architecture conformance is not PECAH TELOR.

## Two-actor / two-line contract review

The 2026-08-21 v2.1 design documents on D: were reviewed in full. Canonical
functional names are used to avoid the earlier Line 1/Line 2 numbering conflict:

- Wake Line: bounded actor wake-up only; it is not an MCP control plane;
- Decision Fabric Line: scoped semantic observation and proposal through P0/P1;
- Executive scope: company-wide observe/analyze/propose;
- Division scope: one reusable division template first, scoped
  observe/propose only;
- Hermes income-operator: single operational control plane;
- DIE State Manager: sole canonical physical writer.

BrowserOS Executive wake and unofficial Division OAuth PKCE remain design-only
actuators. They are not part of PR #12 and require separate security contracts
and Founder authorization. Runtime Decision Fabric must never expose generic raw
filesystem tools. The proposed living_server/living_machine implementation may
only be adapted selectively; it may not create a second control plane or bypass
Decision Gateway and State Manager.

## Next controlled action

1. Founder reviews and merges draft PR #12; no runtime state artifact is part of
   the PR.
2. After merge, synchronize C:\DIE\main and rerun the Decision Fabric targeted
   tests plus full bridge regression.
3. Select and commit M-001, one zero-cost revenue mission, then run Organism Test
   Day 1 through P0/P1 against real Kanban, evidence, artifact, and market
   signals.
4. Keep P2 tunnel-client and both wake actuators dormant until their explicit
   gates.

No secret, paid control plane, dashboard, new worker, or additional transport is
required for these actions.

## Operating doctrine

Build > Run > Verify > Refactor > Extend

Do not restart the repository.
Do not build the dashboard yet.
Do not activate Division runtime yet.
Do not merge Line 2 mutation into Line 1.
Do not reuse Architect DEV trust for runtime cognition.
Do not expose raw paths, credentials, tunnel IDs, or DEV capability.
Do not stage, discard, or rewrite live state/projection/organism artifacts.
Do not write synthetic decisions to live canonical state.
Ship executable artifacts, not architecture theater.
First real money remains the organism fitness signal.

## Agency identities and limited Runtime MCP v1 — 2026-08-22

Founder rejected activation of M-001 until the four-ChatGPT trust boundary is
measurable. Economic validation remains paused. This is an authorized
foundation delta, not permission to select, commit, or execute an income stream.

### Repository standing

- remote `main`: `2aab4b08330eaed16ff2237c5305fc9371480e9d` (PR #12 merged);
- working branch: `architect/agency-identities-limited-mcp-v1`;
- base synchronization in this Architect workspace: complete;
- VPS `C:\DIE\main` synchronization: not claimed from this environment;
- publication: draft PR #13 open from the feature branch to `main`;
- P2 tunnel-client remains deferred post-PECAH-TELOR;
- Executive and Division wake paths remain design-only and were not invoked.

### Four-ChatGPT split

1. Chief Executive Architect DEV remains a Founder-invoked development plane,
   not a runtime identity and not a participant in mission execution.
2. `chatgpt-plus-executive` is company-portfolio cognition. BrowserOS neo
   `127.0.0.1:9010` is wake-only; Decision Fabric is a separate bounded line.
3. `division-head-division01` is a concrete `DIVISION-01` decision identity. No
   income stream is assigned merely by instantiation.
4. `chatgpt-creator` is a Proxima production engine for one job workspace. It
   receives no Decision Fabric tools and has no mission or strategy authority.

The registry now contains 7 identities, not the executor prolog's expected 5:
Founder, Executive, Division template, Division-01 instance, Hermes, Worker
template, and Creator. Keeping both templates is required for replaceability;
removing Worker or a template merely to preserve the number 5 is rejected.

### A — Agency Contract

`PROTOCOLS/agency-contract-v0.md` now explicitly enforces:

~~~text
CONSTITUTION > REGISTRY / IDENTITY > AGENCY CONTRACT > COMMITTED STATE
PROPOSE -> COMMIT -> DELEGATE -> REPORT
~~~

It also pins one operational control plane (`hermes-operator`), one canonical
writer (`die-state-manager`), no raw access, silence != consent, amnesia-first
wake behavior, and the exact non-inheritable Architect DEV capability denylist.

### B — Runtime identities

Canonical anchors implemented:

- `IDENTITY/chatgpt-plus-executive.md`;
- `IDENTITY/division-head-division01.md`;
- `IDENTITY/chatgpt-creator.md`.

Three separate compressed 9-line CONTEXT artifacts were also produced for
account upload. They are user-facing context copies, not canonical operational
state and not substitutes for the VPS/repository anchors.

Creator handoff is now explicit: a production result must contain a
workspace-relative `artifact_path` and `evidence_ref`. Browser-only,
conversation-only, or transient Proxima output is `blocked`, never `done`.

### C — Limited Runtime Decision MCP

`bridge/income_os_bridge/runtime_mcp_server.py` is an executable loopback JSON-RPC
MCP transport on `127.0.0.1:8787` with:

- server-pinned principal and registered scope;
- `DIE_MCP_TOKEN` or `OPERATOR_TOKEN`, minimum 32 bytes;
- maximum request size 262144 bytes;
- an explicit allowlist of 11 bounded P0/P1 projection tools plus signed
  `context_snapshot` for Executive;
- only division-filtered `context_snapshot` for Division-01;
- gated `propose_mission`, `pause_mission`, `resume_mission`, `request_audit`,
  `challenge`, and `escalate` according to registered capabilities;
- `buyer_path` and non-empty `kill_criteria` required for mission proposals;
- 60/hour process-local rate gate;
- forbidden raw/traversal/executable/credential-shaped input;
- no filesystem, shell, Git, test, service, credential, Worker-control, or
  arbitrary state-write tool.

Control calls do not mutate mission state directly. They become signed-snapshot
DECISION requests, pass P5 normalization and P6 Decision Gateway validation,
commit through DIE State Manager, then route to Hermes for operational
acceptance. Creator receives zero tools from this MCP.

`wake_chatgpt` is intentionally absent because the Founder scope says wake paths
are design-only. A wake actuator may not be smuggled into the Decision MCP.

### Verification completed

~~~text
python bin/die_company_brain_check.py
PASS: identity_count=7, runtime_identity_count=6

python -m pytest bridge/tests -q
PASS on Founder VPS: 116 passed

isolated Architect workspace regression
PASS: 111 passed, 5 skipped

python -m py_compile (authority, projection, runtime_mcp_server)
PASS

git diff --check
PASS

manual bounded mission request -> State Manager stub -> Hermes route
PASS

loopback HTTP token rejection + Division-01 tools/list
PASS
~~~

No live state, projection, organism evidence, credential, token value, OAuth
profile, conversation, service, tunnel, Worker, or Proxima runtime was mutated.

### Exact repository manifest — 10 paths

- `LASTSTANDINGPOINT.md`
- `PROTOCOLS/agency-contract-v0.md`
- `company/identity-registry.json`
- `IDENTITY/chatgpt-plus-executive.md`
- `IDENTITY/division-head-division01.md`
- `IDENTITY/chatgpt-creator.md`
- `bridge/income_os_bridge/authority.py`
- `bridge/income_os_bridge/projection.py`
- `bridge/income_os_bridge/events.py`
- `bridge/income_os_bridge/runtime_mcp_server.py`
- `bridge/tests/test_runtime_identities_limited_mcp_v1.py`

### Live Proxima artifact-export gate — PASS

Founder/OpenCode returned an Executor receipt for `T-PROXIMA-PROBE-001`:

~~~text
artifact: C:\DIE\workspaces\T-PROXIMA-PROBE-001\output.png
evidence_ref: evidence/probe.json
worker_contract_normalized: true
result: PASS
~~~

This proves the Creator path can place a real image inside its assigned job
workspace and hand Worker a normalized artifact/evidence pair. The receipt is
the acceptance evidence; neither the generated binary nor mutable VPS evidence
is added to this foundation commit. The closed contract remains mandatory:
browser-only or transient output is `blocked`, never `done`.

### Git publication receipt

- implementation commit: `26e1ffe87730788ca82cc71c557646df086d52cf`;
- branch: `architect/agency-identities-limited-mcp-v1`;
- base: `main` at `2aab4b08330eaed16ff2237c5305fc9371480e9d`;
- draft PR: `https://github.com/kopikonkf/income-os/pull/13`;
- PR state at handoff: `OPEN`, `DRAFT`, merge state `CLEAN`;
- PR manifest: exactly the 10 paths listed above;
- repository checks: none configured/reported for the feature branch;
- acceptance evidence: Company Brain PASS, VPS bridge regression 116 passed,
  `git diff --check` PASS, and live Proxima probe PASS.

Five tracked state/projection changes and two untracked organism-test artifacts
were preserved on the VPS and remained unstaged. They are not present in either
the foundation commit or draft PR.

### Next controlled action

Founder reviews draft PR #13. If accepted, Founder authorizes merge; Architect
does not merge by inference. After merge, synchronize VPS `main`, rerun Company
Brain plus bridge regression, and verify the Runtime MCP baseline before any
income-stream selection. M-001 remains unselected and uncommitted until this
foundation PR is reviewed and merged.

## Post-merge Runtime MCP binding baseline — 2026-08-22

PR #13 was Founder-merged as
`dba3ffa30a144da0237386423b2fcc347b1e61a3`. VPS `main` was synchronized to
that exact SHA without stashing, discarding, staging, or rewriting live state.

Post-merge verification on the Founder VPS:

~~~text
python bin/die_company_brain_check.py
PASS: identity_count=7, runtime_identity_count=6

python -m pytest bridge/tests -q
PASS: 116 passed

python -m py_compile (authority, projection, runtime_mcp_server)
PASS

git diff --check
PASS

staged paths
0
~~~

### Measured transport baseline

Two temporary loopback probes used disposable test tokens and performed no
Decision/state call:

- Executive: principal `chatgpt-plus-executive`, 18 tools, unauthenticated
  request `401`, operational control plane and canonical writer correctly
  advertised;
- Division: principal `division-head-division01`, 6 tools, unauthenticated
  request `401`, single-division scope correctly advertised;
- Creator: 0 Decision MCP tools by contract;
- both temporary processes stopped cleanly after `initialize` + `tools/list`.

### Port collision discovered

Production binding to `127.0.0.1:8787` is invalid on the live VPS. That port is
already occupied by the Architect DEV Living MCP. Local infrastructure also
uses `8789` for OAuth edge and `8790` for the Architect gateway. Reusing any of
those ports would violate DEV/runtime separation.

Because the Runtime MCP process is server-pinned to one principal, Executive
and Division require distinct instances. The corrected binding contract is:

- Executive Runtime Decision MCP: `127.0.0.1:8791`;
- DIVISION-01 Runtime Decision MCP: `127.0.0.1:8792`;
- `8787`, `8789`, and `8790`: fail-closed infrastructure-reserved ports;
- explicit alternate ports remain available only for bounded test execution.

Implementation branch: `architect/runtime-mcp-bindings-v1`. This correction
does not create services, provision/read secrets, invoke a tunnel, implement a
wake actuator, or activate an income stream.

Binding-correction verification on the Founder VPS:

~~~text
python -m pytest bridge/tests -q
PASS: 118 passed

default Executive binding -> 127.0.0.1:8791 -> 18 tools
PASS

default DIVISION-01 binding -> 127.0.0.1:8792 -> 6 tools
PASS

Architect DEV listener 127.0.0.1:8787 preserved
PASS

temporary Runtime MCP processes stopped after probe
PASS
~~~

### Binding-correction publication receipt

- implementation commit: `b89702e`;
- branch: `architect/runtime-mcp-bindings-v1`;
- draft PR: `https://github.com/kopikonkf/income-os/pull/14`;
- base: merged `main` at `dba3ffa30a144da0237386423b2fcc347b1e61a3`;
- manifest: 5 paths;
- persistent services, production tokens, wake actuators, and tunnels: not
  created or invoked.

### Next controlled action

Founder reviews draft PR #14; Architect does not merge by inference. After
merge, create a separate activation contract for two per-principal Runtime MCP
services and secure token provisioning, then prove live `initialize`,
`tools/list`, and read-only `context_snapshot` for each identity. Wake
actuators and P2 remain outside that activation. M-001 remains unselected and
uncommitted.

## Two-principal Runtime MCP activation contract — 2026-08-22

Founder merged PR #14 as
`bc1d38d37f18fb9678297a1c5ab74abce770a7dd`. VPS `main` was synchronized to
that exact merge commit without touching live runtime state. Post-merge Company
Brain validation passed and the full bridge regression remained `118 passed`.

The next foundation gate was implemented on
`architect/runtime-mcp-activation-v1`. This is an activation contract, not a
production activation. It creates no secret, Windows service, process, wake,
tunnel, Decision call, or mission during repository validation.

### Measured supervisor baseline

VPS inspection established:

- NSSM, WinSW, and PM2 are not installed or available;
- the existing Aether Windows service uses an internal Python SCM host;
- the service host owns its child process tree through a Windows Job Object;
- `C:\ProgramData\DIE\RuntimeMCP` did not exist before this contract;
- ports `8791` and `8792` remained available for the two Runtime MCP instances.

The DIE contract therefore uses a repository-native SCM host rather than adding
a new third-party supervisor or misusing Scheduled Tasks as services.

### Activation artifacts

- `ops/windows/runtime-mcp/die-windows-service.py` — SCM lifecycle host with
  Job Object child-tree ownership and no command/secret receipt;
- `Initialize-DIERuntimeMcpActivation.ps1` — default `Plan`; explicit,
  interactive `Provision` for fixed directories, restrictive ACLs, and four
  secret files per principal (eight total after the edge/OAuth revision);
- `Install-DIERuntimeMcpServices.ps1` — default `Plan`; explicit `Install` for
  two Automatic LocalSystem services with rollback and recovery actions;
- `Invoke-DIERuntimeMcp.ps1` — exact principal/port launcher that loads only
  its lane's protected token and snapshot signing material;
- `Test-DIERuntimeMcpActivation.ps1` — `Plan`, metadata-only `Installed`, and
  bounded authenticated `Live` verification modes;
- `docs/operations/RUNTIME_MCP_ACTIVATION_V1.md` — ordered Founder/local
  operator runbook and exclusions;
- `bridge/tests/test_runtime_mcp_activation_v1.py` — repository safety and
  contract regression.

Fixed service bindings:

| Service | Principal | Binding | Expected tools |
| --- | --- | --- | --- |
| `DIERuntimeMCPExecutive` | `chatgpt-plus-executive` | `127.0.0.1:8791` | 18 |
| `DIERuntimeMCPDivision01` | `division-head-division01` | `127.0.0.1:8792` | 6 |

`8787`, `8789`, and `8790` remain fail-closed infrastructure-reserved ports.
Creator remains outside Decision MCP with zero tools.

### Security and execution gates

1. `Plan` is the default for provisioning, installation, and verification and
   does not access ProgramData or mutate services.
2. `Provision` requires a directly attached local console plus explicit switch.
   Values are entered twice with `Read-Host -AsSecureString`; existing roots are
   never overwritten; a partial provision is rolled back.
3. Each principal has a separate bearer token, HMAC key, and HMAC key ID under
   ACLs limited to Local System, Administrators, and the provisioning operator.
4. `Install` reads secret metadata only, rejects occupied/reserved ports and
   existing services, embeds no secret in SCM, and does not start services.
5. `Live` assumes already-running services. It performs only HTTP 401,
   `initialize`, `tools/list`, and read-only signed `context_snapshot` checks.
   Token values are read locally for authentication but never returned.
6. Real provisioning may not be executed through chat or Architect MCP. It is
   reserved for Founder or an explicitly delegated local VPS operator after
   merge.

### Verification and publication receipt

~~~text
PowerShell Initialize Plan
PASS: side-effect-free JSON contract

PowerShell Install Plan
PASS: side-effect-free JSON contract

PowerShell Verify Plan
PASS: side-effect-free JSON contract

targeted activation regression
PASS: 9 passed

python bin/die_company_brain_check.py
PASS: identity_count=7, runtime_identity_count=6

python -m pytest bridge/tests -q
PASS: 127 passed

python -m py_compile
PASS

git diff --cached --check
PASS
~~~

- implementation commit: `51141929201a674d350839b61a5c4e3207fb0dd7`;
- branch: `architect/runtime-mcp-activation-v1`;
- draft PR: `https://github.com/kopikonkf/income-os/pull/15`;
- initial PR state: `OPEN`, `DRAFT`;
- implementation manifest: exactly 7 activation paths before this canonical
  handoff update;
- five tracked state/projection changes and two untracked organism-test
  artifacts remained unstaged and excluded.

No real token or signing key was requested, read, generated, provisioned, or
returned. No Windows service was installed or started. BrowserOS and Division
wake remain design-only; P2 tunnel remains deferred post-PECAH-TELOR; Creator
and Proxima were unchanged; M-001 remains unselected and uncommitted.

### Next controlled action

Founder reviews draft PR #15. Architect does not merge or provision by
inference. After Founder merge, synchronize VPS `main`, rerun the full
regression and all three Plan modes, then obtain explicit local authorization
for the ordered `Provision -> Install -> Start -> Live` gates. Only a Live PASS
for both pinned identities establishes the measurable runtime baseline needed
before any income-stream selection.

## Founder edge transport lock — 2026-08-22

Founder placed draft PR #15 on merge hold and accepted the per-principal Runtime
MCP separation while correcting the public transport contract. Runtime MCP must
reuse the existing zero-cost self-hosted Cloudflare Tunnel under the
Founder-owned `aethers.web.id` zone. P2 OpenAI `tunnel-client`, OpenAI billing,
and any control-plane API key remain deferred and out of scope.

Architect inspected the standalone `D:\mcp-architect` implementation and the
active edge topology without reading its ignored `.env`, token file, temporary
files, or Cloudflare credential contents. The proven Architect pattern is:

~~~text
public hostname -> existing Cloudflared tunnel -> standalone MCP process
                                                 (OAuth/PKCE + MCP resource)
~~~

It does **not** use Aether Caddy. The Caddy listener at `127.0.0.1:8080`
belongs to a separate Aether codebase and must not become a DIE dependency.
Runtime therefore owns two direct, deny-by-default routes:

| Public hostname | Loopback upstream | Pinned principal | Tools |
| --- | --- | --- | --- |
| `executive-mcp.aethers.web.id` | `127.0.0.1:8791` | `chatgpt-plus-executive` | 18 |
| `division01-mcp.aethers.web.id` | `127.0.0.1:8792` | `division-head-division01` | 6 |

One hostname maps to one principal process. There is no shared endpoint, proxy
token router, cross-lane bearer, or inherited Architect capability. Each
Runtime process embeds its own OAuth metadata, dynamic client registration,
Founder login/consent, PKCE S256 authorization-code exchange, refresh flow, and
`/mcp` protected resource. Its OAuth signing root is derived from that lane's
separate protected bearer material.

Read-only audit found that the two direct Cloudflared routes and their CNAMEs
already existed outside this Architect change; full ingress validation passed
and the config retained a terminal `http_status:404`. Architect did not create,
alter, reload, or restart any edge component. Ports `8791` and `8792` remained
without listeners, so the observation is not a public connector activation or
proof.

Repository revision scope for the held PR now includes:

- embedded, principal-pinned OAuth/PKCE support in the existing Runtime MCP;
- one additional protected no-echo OAuth login password per principal (eight
  activation secret files total, with values never entering repository/chat);
- direct Cloudflared ingress fragment with no tunnel credential or Aether route;
- plan-first edge mutation and read-only verification scripts;
- an edge runbook with the explicit Free-account empirical registration gate;
- regression coverage for PKCE, refresh, one-time codes, cross-principal token
  rejection, direct routes, zero Caddy/P2 dependency, and side-effect-free Plan
  receipts.

If DIVISION-01 Free-account connector registration is rejected, the required
fallback is the already designed wake/OAuth conversation path. No paid upgrade,
P2 activation, or Executive-scope broadening may be inferred. M-001 remains
unselected until both runtime lanes have measurable receipts.

No secret was requested, generated, read, or provisioned. No service was
installed or started; no Cloudflared config, DNS, Caddy route, wake path,
Proxima flow, state event, or mission was mutated by this revision.

### Edge revision verification receipt

~~~text
PowerShell activation Plan modes (Initialize / Install / Test)
PASS: 3/3 side-effect-free JSON contracts

PowerShell edge Plan modes (Set / Test)
PASS: 2/2 side-effect-free JSON contracts

python bin/die_company_brain_check.py
PASS: identity_count=7, runtime_identity_count=6

python -m pytest bridge/tests -q
PASS: 134 passed

python -m py_compile
PASS

git diff --check
PASS
~~~

The regression includes a temporary loopback HTTP subprocess proof for health,
OAuth metadata, unauthenticated 401, and the 18-tool Executive listing. The
test process was terminated by the test and did not install or start a Windows
service. Edge modes `Configured`, `Public`, `ApplyIngress`, and `ApplyDns` were
not executed. The implementation manifest is 14 repository paths. Pre-existing
tracked state/projection changes and three untracked organism-test artifacts
remain excluded from staging.

### Edge revision publication receipt

- implementation commit:
  `92fa916b5008f48db4629e00a5444b176ac533a3`;
- branch: `architect/runtime-mcp-activation-v1`;
- draft PR: `https://github.com/kopikonkf/income-os/pull/15`;
- PR status after push: `OPEN`, `DRAFT`, `MERGEABLE`;
- local implementation head matched the remote branch head exactly;
- staged path count after push: `0`;
- installed Runtime MCP service count: `0`;
- listeners on ports `8791` and `8792`: `0`;
- GitHub checks reported: none configured for the branch.

The pre-existing state/projection and organism-test worktree artifacts remain
present, unstaged, and excluded. This receipt is documentation of the push, not
authorization to merge or activate.

### Revised gate order

~~~text
Founder review + merge
  -> sync C:\DIE\main + full regression + all Plan modes
  -> interactive local Provision                  [separate authorization]
  -> SCM Install + Start                           [separate authorization]
  -> loopback 401/init/tools/signed snapshot proof [separate authorization]
  -> direct Cloudflared + DNS verification/apply   [separate authorization]
  -> Executive account connector proof
  -> DIVISION-01 Free registration experiment
  -> fallback wake/OAuth if Free registration is blocked
  -> only then M-001/income-stream selection
~~~

### Next controlled action

Founder reviews draft PR #15 and decides whether to merge. Architect does not
merge, provision, install, start, edit edge production, register a connector,
or select M-001 by inference.

## Two-principal Runtime MCP E2E activation — 2026-08-22

Founder merged PR #15 as
`7f5b99af653042b1e1bd85799a1ba60eafd101bc`, then completed the separately
authorized activation gates through a local OpenCode executor. This is the
first complete cloud-to-loopback proof for both Runtime Decision principals.

| Lane | Account | Public endpoint | Service / binding | Tools | Signed snapshot | Scope | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Executive | ChatGPT Plus | `https://executive-mcp.aethers.web.id/mcp` | `DIERuntimeMCPExecutive` / `127.0.0.1:8791` | 18/18 | `SNAP-5B3863A47162B024` | `company_portfolio` | PASS |
| DIVISION-01 | ChatGPT Free | `https://division01-mcp.aethers.web.id/mcp` | `DIERuntimeMCPDivision01` / `127.0.0.1:8792` | 6/6 | `SNAP-456CE0AED2BEC70F` | `single_division` | PASS |

Both services run as Automatic LocalSystem services with configured failure
recovery. Each public endpoint travels directly through the existing
self-hosted Cloudflare Tunnel to its pinned loopback process. Unauthenticated
MCP requests returned HTTP 401; authenticated snapshots were fresh,
HMAC-signed, and carried a key ID. Cross-principal tokens were rejected.

Measured compliance remained intact:

- one hostname, port, service, bearer root, and principal per lane;
- no shared endpoint or token-based proxy routing;
- zero raw filesystem, shell, Git, service-control, or credential tools;
- no `wake_chatgpt` tool in either Runtime MCP surface;
- Caddy Aether remained outside the request path;
- P2 OpenAI `tunnel-client` remained dormant;
- eight protected secret files stayed server-side and were never returned.

The DIVISION-01 receipt is empirical proof that the assigned ChatGPT Free
account can register and use this custom MCP connector. OpenAI documentation
does not establish that as a universal Free-account entitlement, so the project
records the measured account result without generalizing beyond it.

### Upstream defects discovered during activation

1. `Install-DIERuntimeMcpServices.ps1` used nested quoting through
   `sc.exe create`; Windows PowerShell 5.1 mangled the `binPath` arguments and
   produced `Invalid start= field`. Founder installed the same contract with
   `New-Service` as a local workaround.
2. `Test-DIERuntimeMcpActivation.ps1 -Mode Live` evaluated `.Count` directly
   on an empty `Where-Object` pipeline under `Set-StrictMode -Version Latest`.
   The crash occurred after the actual checks had passed.

Repository fixes are isolated on
`architect/runtime-mcp-live-hotfix-v1`, based on the exact PR #15 merge commit:

- replace only the creation call with PowerShell 5.1 `New-Service`, while
  retaining `sc.exe` for recovery configuration and rollback deletion;
- verify created service metadata is `Auto` plus `LocalSystem`;
- array-wrap the verifier's filtered secret-check pipeline before `.Count`;
- add regression assertions for both defects and persist this live receipt.

Architect did not read any secret, reinstall/restart either live service, run
the Live verifier, modify DNS/Cloudflared/Caddy, invoke wake, change Proxima, or
select M-001 while preparing the hotfix. Pre-existing state/projection and
organism-test artifacts remain unstaged and excluded.

### Hotfix verification receipt

~~~text
PowerShell activation Plan modes (Initialize / Install / Test)
PASS: 3/3 side-effect-free JSON contracts

PowerShell edge Plan modes (Set / Test)
PASS: 2/2 side-effect-free JSON contracts

targeted activation regression
PASS: 10 passed

python bin/die_company_brain_check.py
PASS: identity_count=7, runtime_identity_count=6

python -m pytest bridge/tests -q
PASS: 135 passed

python -m py_compile
PASS

git diff --check
PASS
~~~

No Install, Installed, Live, Configured, Public, ApplyIngress, or ApplyDns mode
was invoked for this verification. The already-running Runtime MCP services and
their edge paths were left untouched.

### Hotfix publication receipt

- implementation commit:
  `bdd98968b16f6d89a60de75b0f36261df3b6ac61`;
- branch: `architect/runtime-mcp-live-hotfix-v1`;
- draft PR: `https://github.com/kopikonkf/income-os/pull/16`;
- base: PR #15 merge commit
  `7f5b99af653042b1e1bd85799a1ba60eafd101bc`;
- initial PR status: `OPEN`, `DRAFT`, `MERGEABLE`;
- implementation manifest: exactly five repository paths;
- staged state/projection/organism-test artifacts: `0`.

After repository verification, a read-only service check still showed both
Runtime MCP services `Running` and `Automatic`, with exactly two loopback
listeners on ports `8791` and `8792`. This observation confirms non-disruption;
it is not a second activation action.

### Next controlled action

Complete Plan and repository regression for the two upstream fixes, publish a
draft hotfix PR, and return control to Founder. After Founder merges and the
operator confirms the repaired scripts, M-001 ratification may begin as a
separate controlled mission decision; wake and P2 remain deferred.

## M-001 ratification, acceptance, and reconciliation standing — 2026-08-23

M-001 is the first ratified and operationally accepted mission:

| Receipt | Canonical meaning | Timestamp |
| --- | --- | --- |
| D-0020 | Founder RATIFY M-001 v1 | T0 = 2026-08-22T17:13:25Z |
| D-0021 | DIVISION-01 `propose_mission`; canonical mutation true | 2026-08-22T18:13:49Z |
| D-0022 | Hermes operational acceptance | 2026-08-22T18:18:01Z |

Executive snapshot at 2026-08-22T18:20:58Z / bridge seq 452 independently
verified the ratification and acceptance evidence with no portfolio conflict.
Day-45 hard falsification deadline is 2026-10-06.

M-001 cohort remains Adobe Stock, Dreamstime, 123RF, Vecteezy,
MotionElements, plus the Magnific warm lane. The cost envelope is USD 0.
CPU upscaler gate passed with `realesr-general-x4v3`: p50 32.3 seconds, p95
33.5 seconds, RAM 2.4% of 56 GB, and 37.7 MP output at 4x. CPU-inline routing is
allowed; this does not authorize production.

### Canonical mismatch diagnosis

`active_missions: []` was a projection defect, not absence of mission
acceptance. The decision ledger contains the full lifecycle while the old
projection seeded missions only from `EVENTS.jsonl`. No M-001 event or linked
Kanban row existed, so the accepted mission disappeared from the bounded
surface.

The canonical correction is:

- mission status compiles from the highest valid mission decision;
- D-0022 makes M-001 `active` even if Kanban materialization is late;
- Kanban remains Hermes' operational materialization, not a second mission
  authority;
- missing mission-linked materialization sets `reconcile_required=true`,
  `execution_ready=false`, and degraded completeness;
- only exact CLI `mission_id=M-001` or a canonical `mission_id` + `task_id`
  event relation clears reconciliation;
- unrelated open cards never count toward M-001.

The SQLite fallback cannot prove the relation because its verified schema has
no `mission_id` column. Title matching, assignee matching, and card-order
matching are forbidden inference.

### Health and writer hardening

Production remains blocked. The known conditions are provider main 429,
die-heartbeat Kanban CLI `WinError 2`, and `gateway_running=false`.

This patch adds a fail-closed `execution_readiness` surface and an explicit
append-only alarm lifecycle. WARNING/CRITICAL records remain active until a
later event resolves their exact event ID or stable dedupe key. The heartbeat
cron opens and resolves its Kanban-CLI alarm based on actual read failure or
success and supports an explicit `DIE_HERMES_EXE` executable override.

The State Writer now rejects `mission_ratification` unless request ID,
division ID, and mission ID are present. It also rejects any semantic object
that would otherwise be silently discarded for lack of request ID. This is the
regression guard for D-0019.

### Snapshot relay standing

Two chat relays failed signed snapshot integrity; the byte-exact programmatic
loopback submission passed. Chat is not an approved transport for large signed
snapshot JSON. A future one-use opaque `snapshot_ref` contract is specified in
`docs/architecture/MISSION_STATE_RECONCILIATION_V1.md`, but no Runtime MCP or
wake schema changes are part of this patch.

### Versioned artifacts

- `LASTSTANDINGPOINT.md`
- `bin/die_cron.py`
- `bin/die_event.py`
- `bridge/SCHEMA_NOTES.md`
- `bridge/income_os_bridge/events.py`
- `bridge/income_os_bridge/projection.py`
- `bridge/tests/test_mission_reconciliation_v1.py`
- `bridge/tests/test_runtime_identities_limited_mcp_v1.py`
- `docs/architecture/MISSION_STATE_RECONCILIATION_V1.md`
- `docs/operations/M001_RECONCILIATION_AND_HEALTH_GATE_V1.md`

No state JSONL, projection output, service, secret, DNS, wake, P2, Proxima,
production asset, or marketplace submission is included.

### Verification result

```text
M-001 + division identity targeted regression: 17 passed
Full bridge regression: 136 passed, 7 skipped
python -m py_compile: PASS
python bin/die_company_brain_check.py: PASS
git diff --check: PASS
```

The skipped tests are existing platform-specific checks. The first full-suite
attempt from Linux used the canonical Windows default `C:\DIE` and therefore
failed to locate the identity registry. Re-running with `DIE_HOME` bound to the
repository checkout produced the clean result above. No runtime state was
written.

### Next controlled action

The GitHub App write scope was repaired by Founder. The verified implementation
tree was published to remote branch
`architect/m001-mission-reconciliation-v1` as commit
`e66535d7bfc64598656e8397d31b74cefcf564e4`, then opened as draft PR #18:

https://github.com/kopikonkf/income-os/pull/18

Initial PR receipt: OPEN, DRAFT, base `main` at
`68f81d1bfc863f7c71448cf5fd63420904ec44f2`, exactly 10 changed paths, 1052
additions, and 45 deletions. Local implementation commits remain
`03f2e1dedcfd0ba274d17b4e462c0a497a6500c0` and
`4c19841ffc039ddbf876a76c400ad8ca0358a759`; GitHub created the equivalent
remote commit from the verified tree because the local HTTPS checkout had no
non-interactive credential.

Founder reviews draft PR #18 and decides whether to merge. After merge, Hermes
may materialize the M-001 mission root through the canonical operational
interface. Production starts only after both mission materialization and the
health readiness gate pass under the existing A0 controls.

## Wake E2E, Executive verdict, and security canon — 2026-08-23

### Updated operational standing

M-001 reconciliation is PASS:

- `status=active`;
- `lifecycle_state=materialized`;
- `reconcile_required=false`;
- `execution_ready=true`;
- active CRITICAL alarms: 0;
- root card `t_3d062e86`, canonical relation event E-000516;
- batch-1 blueprint task `t_7ded3fac` is RUNNING;
- Worth-Making Gate remains pending Founder decision.

The Kanban umbrella dependency was removed because it blocked child claiming.
Mission linkage remains canonical through `mission_id + task_id`; parent-child
Kanban structure is not mission identity.

Division-01 wake is LIVE E2E through headed Brave in-page fetch over loopback
CDP :9333. Executive wake is LIVE through BrowserOS neo CDP :9110. Hermes sent
the first Executive STRATEGIC wake and received: `No portfolio veto. Proceed to
canon with mandatory annotations.` Evidence is committed at
`evidence/executive-verdict-wake-design-20260823.json` (E-000535).

Repository receipts:

- PR #18 merged as `362a386f22ad415d49d8ed4c1d365642ce0b3f67`;
- PR #19 remains the separate M-001 evidence receipt;
- PR #20 merged as `6cee35071919f1315620c697aa933f4ca1069498`;
- Executive wake implementation: `c9b6c5c10c2df61fc6a05db3fb9f7626eb6024f0`;
- Executive verdict receipt: `acb4109e7977b3deda31f3d428b94fb0e6ee724b`.

### Architect verdict

Overall verdict: **APPROVE WITH MANDATORY CONTROLS**.

Ratified decisions:

1. Wake is outbound control-plane transport and remains outside Runtime MCP.
2. Executive uses the existing principal-dedicated BrowserOS neo web session;
   no separate Codex OAuth credential is created solely for wake.
3. Each division has exactly one active persistent continuity thread, with
   explicit supersession lifecycle. A thread is continuity memory, not Company
   Truth.

Mandatory auth/session corrections:

- Web JWT remains inside page memory and no longer crosses CDP into Python.
- Sentinel requirement token remains page-scoped; response/auth bodies are not
  returned into errors or logs.
- Browser profile cookies and full CDP are credential-equivalent and require
  loopback-only binding plus principal-dedicated OS storage.
- Codex `auth.json` is a separate credential domain, not a wake dependency;
  OS credential store is preferred, protected file fallback is conditional.
- `wake.json` remains secret-free but now carries principal/division binding,
  one active thread, generation, and bounded supersession history.
- Auth failures stop blind retry and enter sanitized recovery/escalation.

### Multi-division v2.1 correction

The pure-OAuth/raw-HTTPS assumption is retired for the empirically measured web
wake path. Browser-backed in-page transport is canonical until a supported API
replaces it.

The proposed `one browser process + many profiles` layout is not accepted as a
cross-division security boundary because one full-CDP controller can reach the
process targets. Canon is one browser binary plus principal-dedicated user-data
directories and a bounded pool of on-demand browser slots, default concurrency
one. This avoids 15 always-on browser processes without collapsing 15
credential domains into one shared compromise domain.

Current implementation gap is explicit: the Division-01 startup script still
selects `Profile 3` inside the ordinary Brave `User Data` root. It remains an
accepted single-principal pilot only. Before Division-02, an authorized operator
must migrate it to a principal-dedicated user-data directory and prove the CDP
process exposes no other principal targets. This branch does not mutate the
live browser profile or force re-authentication.

Expansion beyond Division-01 remains blocked until the first M-001 production
cycle and 20 eligible wake attempts provide reliability, recovery, latency,
thread-binding, and zero-leakage evidence.

### Versioned artifacts

- `bin/wake_division01.py`
- `bin/wake_executive.py`
- `bin/wake_brave_health.ps1`
- `skills/wake-chatgpt/SKILL.md`
- `skills/wake-executive/SKILL.md`
- `bridge/tests/test_wake_security_canon_v1.py`
- `docs/architecture/WAKE_AUTH_SESSION_SECURITY_V1.md`
- `docs/operations/WAKE_AUTH_SESSION_ROTATION_V1.md`
- `LASTSTANDINGPOINT.md`

Explicit exclusions: no credential value was requested or read; no browser
profile/session, task scheduler, service, CDP process, Runtime MCP, DNS,
Cloudflared, state JSONL, wake execution, M-001 production, or marketplace
submission was mutated.

### Verification result

```text
Wake security canon targeted regression: 6 passed
Full bridge regression: 142 passed, 7 skipped
python -m py_compile: PASS
python bin/die_company_brain_check.py: PASS (7 identities / 6 runtime identities)
git diff --check: PASS
```

The skipped checks are pre-existing platform-specific tests. Test dependencies
were installed only under `/tmp`; no dependency or runtime state was added to
the repository.

### Publication receipt and next controlled action

The verified tree was published through the authorized GitHub Connector to
`architect/wake-security-canon-v1` as remote commit
`491dc7436da39270b14a48f46da047668d794473`. Draft PR #21 is OPEN:

https://github.com/kopikonkf/income-os/pull/21

Initial receipt: base `main` at
`acb4109e7977b3deda31f3d428b94fb0e6ee724b`, 9 changed paths, 669 additions,
26 deletions, draft=true, merged=false. The equivalent verified local commit is
`46a94cc8e8795d8775312558ed435a68d59d3a16`; both commits point to tree
`b8b4f6866a90f673d2f0105d77beb0b8e6c72e64` before this receipt-only update.

Founder reviews draft PR #21 and decides merge. Runtime deployment and the
principal-dedicated profile migration remain separate authorized operator
actions. Blueprint batch-1 proceeds only to the Founder Worth-Making Gate under
the existing A0 controls.

---

## 2026-08-24 — Two-Principal Canon Assimilation v1

Repository baseline: `eb8cdecd7ca91c1f0ff3a8a1cce90be8c7fb8bd0`

Working branch: `architect/two-principal-canon-assimilation-v1`

### Standing

- Hermes canon assimilation receipt: `PASS` at the baseline above, as reported
  by the authorized operator.
- Executive transport: live on wake `:9010` / BrowserOS CDP `:9110` with
  principal-pinned Decision MCP `:8791`.
- Division-01 transport: live on dedicated Brave CDP `:9333` with
  principal-pinned Decision MCP `:8792`.
- Executive fresh-context canon assimilation: `NOT YET PROVEN`.
- Division-01 fresh-context canon assimilation: `NOT YET PROVEN`.

### Canon-load decision

No new port, transport, MCP tool, filesystem access, state writer, or execution
authority is introduced. The existing wake lanes may deliver bounded canon
briefings pinned to an exact repository revision; each principal must reload
current mission truth from its own `context_snapshot`.

For active M-001 cognition:

- Division-01 must load Pipeline Canon, Human-Centric Atlas Canon, and the
  Founder-ratified Blueprint v2 before research, scoring, Worth-Making Gate,
  proposal, or reporting.
- Executive must load Pipeline Canon at boot and load Atlas Canon plus
  Blueprint v2 before M-001 assessment, challenge, recommendation, or
  reporting.
- The dated platform matrix is conditional input for eligibility, packaging,
  distribution, and contract-risk decisions.
- The quantity workbook is consumed only through a bounded, versioned
  formula/result digest and remains a gross-revenue hypothesis model, not
  observed ERVA or net-profit evidence.

### Verification

```text
Targeted canon/blueprint/role regression: 12 passed
Full bridge regression: 154 passed, 7 skipped
Company Brain validator: PASS (7 identities / 6 runtime identities)
git diff --check: PASS
```

The full suite was run on Linux with `DIE_HOME` pinned to the repository root;
the default runtime path remains `C:\DIE` for the Windows deployment. Test-only
Python dependencies were installed under `/tmp` and were not added to the
repository.

### Publication receipt and next controlled action

Draft PR #27 is open:

https://github.com/kopikonkf/income-os/pull/27

Initial remote implementation commit:
`ade4ffbe630bf319285b45d6291ff00807619703`. The PR targets `main` at
`eb8cdecd7ca91c1f0ff3a8a1cce90be8c7fb8bd0`; its four implementation paths
match the verified local tree.

Founder reviews and merges PR #27. After merge, the authorized operator syncs
`C:\DIE`, wakes Executive and Division-01 in fresh contexts, and captures two
independent assimilation receipts containing principal ID, merged SHA,
documents loaded, snapshot ID/as-of, probe results, and `PASS|FAIL`.

Worth-Making Gate execution remains blocked until the Division-01 receipt is
`PASS`. This docs/test change does not authorize production, submission,
publication, account action, or spend.

---

## 2026-08-24 — Runtime Canon Context Projection v1

Repository baseline: `4e3cf11e2095453c94562e0dfa1cdd731275784e`

Working branch: `architect/runtime-canon-context-projection-v1`

### Standing

- PR #27 is merged at the baseline above.
- Independent fresh-context wake receipts for Executive and Division-01 are
  valid `FAIL` receipts: both principals correctly refused to claim raw canon
  access, and the earlier semantic snapshot did not contain canon content.
- Wake transport is therefore proven, but canon assimilation for these two
  principals remains unproven.
- Worth-Making remains blocked until Division-01 receives a verified semantic
  canon projection and its independent fresh-context receipt is `PASS`.

### Implemented decision

The existing principal-pinned `context_snapshot` now includes a
`canon_context` surface for `chatgpt-plus-executive` and
`division-head-division01`. No MCP tool, port, writer, wake transport, or
authority was added.

The surface is built from the strict allowlist in
`company/runtime-canon-context-v1.json`. It fails closed unless the Pipeline
Canon, Human-Centric Atlas Canon, Founder-ratified M-001 Blueprint v2, dated
platform matrix, and quantity workbook match their exact SHA-256 digests. It
returns only repository-relative identifiers, classifications, bounded
decision facts, and role-specific digests. It does not return raw documents or
host paths.

For both principals, canon load is proven only when
`context_snapshot.data.canon_context.load_status = VERIFIED` and that signed
snapshot carries the exact repository SHA, manifest hash, required document
hashes, and correct principal/scope. A wake, port, file name, host path, or
session-memory statement is insufficient.

The matrix remains a dated supporting input. The quantity workbook remains a
formula-mechanics-passing gross-revenue `HYPOTHESIS`; it is explicitly not
observed ERVA, net profit, annualized run-rate, proof of `$1B/3Y` feasibility,
or execution authority.

### Verification

```text
Targeted canon/role/snapshot regression: 34 passed
Full bridge regression: 162 passed, 7 skipped
Company Brain validator: PASS (7 identities / 6 runtime identities)
Source SHA-256 pins: PASS (5/5)
python -m py_compile: PASS
git diff --check: PASS
```

The suite was run on Linux with `DIE_HOME` pinned to the repository checkout;
the governed Windows deployment path remains `C:\DIE`. Test dependencies were
isolated outside the repository. No `state/*` or `workspaces/*` path is part of
the implementation manifest.

### Publication receipt and next controlled action

Draft PR #28 is open:

https://github.com/kopikonkf/income-os/pull/28

Initial remote implementation commit:
`e37d4a6f84ddd357e615008828db9bdbdca0e312`. The PR targets `main` at
`4e3cf11e2095453c94562e0dfa1cdd731275784e`; its nine implementation paths
match the verified local tree.

Founder reviews and merges PR #28. After merge, the authorized operator:

1. fast-forwards `C:\DIE` while preserving runtime-owned state;
2. reloads the Executive and Division-01 Runtime Decision MCP processes so the
   new projection code is live;
3. wakes each principal in a fresh context and requires it to pull its own
   principal-pinned `context_snapshot`;
4. verifies `canon_context.load_status = VERIFIED`, the merged repository SHA,
   five document hashes, correct principal/scope, fresh snapshot ID/as-of, and
   integrity proof;
5. runs independent role-specific canon probes and captures `PASS|FAIL`
   receipts under runtime-owned evidence/state.

Production, upload, publication, account action, spend, and canonical state
mutation remain unauthorized by this change. Worth-Making opens only after the
Division-01 receipt is independently `PASS` and the existing Founder gate is
satisfied.

## M-001 J1-J8 closed-loop runner v1 — 2026-08-24

### Baseline and verdict

- branch: `architect/m001-closed-loop-runner-v1`;
- base: `main` at `d2c3e27a4c0d7affc4c9c82d5ef50d5d362446b6`;
- workflow verdict: **IMPLEMENTED / NOT DEPLOYED / NO PRODUCTION AUTHORITY**;
- execution pattern: one-shot governed mission compiler plus the existing
  Hermes Gateway embedded Kanban dispatcher; no production cron and no second
  control plane.

The live read-only autopsy proved that the income-operator Gateway is running,
Kanban dispatch is enabled at a 60-second interval, and Proxima's loopback
model registry exposes enabled `chatgpt`. The stale v1 M-001 root card remains
unassigned and inert; this implementation does not silently mutate it.

### Implemented contract

`bin/m001_loop.py` now validates a `die.m001.loop-request.v1` against exactly
one Founder-authored `die.decision.v1` record committed by DIE State Manager.
The authority binds run ID, exact Asset Blueprint SHA-256, 20-40 batch size,
five-asset canary, USD 0.00 maximum cost, future expiry, production=true, and
submission/publication=false. Resolvable `VERIFIED` evidence with SHA-256 is
mandatory for canon assimilation, Division-01 Worth-Making, platform contract
matrix, production-engine rights, and Proxima durable artifact export.

After preflight and a live runtime doctor, the compiler creates all eight cards
as blocked, writes durable `RUN.json`, `JOB.json`, and `PROGRESS.md` artifacts,
then releases the dependency graph:

```text
J1 Blueprint lock
-> J2 five-asset canary
-> J3 canary QA
-> J4 remaining five-asset waves
-> J5 full-batch QA
-> J6 eligible recovery / NOT_REQUIRED
-> J7 metadata + manual-submission package
-> J8 READY_FOR_MANUAL_SUBMISSION
```

J2/J4/J6 are the only Proxima-eligible stages, always through bounded Worker
jobs. The single v0 Worker remains sequential. Hermes card retries are disabled
for networked production/recovery stages; ambiguous export becomes `BLOCKED`.
J8 cannot claim submission, marketplace approval, license, or ERVA.

`bin/m001_asset_qa.py` is the executable universal-QA boundary. It verifies
workspace confinement, source SHA-256, structurally valid PNG/JPEG containers,
dimensions, stable lineage, exact duplicates, and durable rights/safety/
watermark/lineage/technical/visual-review evidence. It routes hard failures to
quarantine/recreate states and blocks when visual evidence is absent; it never
implements generic `FAIL -> social`.

J8 additionally proves the blueprint lock, J2/J4 manifest schemas and counts,
J3/J5 source-manifest hashes, 20-40 unique asset IDs, one full-batch QA route
per asset, at least 80 percent universal-QA pass, zero hard-rights failures,
zero unauthorized cost, and an exact J7 package containing every and only
`T1_PASS` asset.

### Proxima boundary discovered

Read-only source inspection found that the currently running Proxima v5 REST
schema exposes `/v1/chat/completions` and the ChatGPT engine currently returns
text content. Durable binary export is therefore not inferred from API health.
The earlier `T-PROXIMA-PROBE-001` receipt remains the evidence input, but every
live asset must independently resolve inside its Worker workspace. Browser-only
or transient output is `BLOCKED`, never `done`. The five-asset canary is the
first governed reproducibility test of that export procedure.

### Verification

```text
Targeted M-001 runner/QA regression: 13 passed
Full Linux bridge regression: 175 passed, 7 skipped
Company Brain validator: PASS (7 identities / 6 runtime identities)
python -m py_compile: PASS
git diff --check: PASS
```

The Linux worktree required `DIE_HOME` pinned to the checkout and
`DIE_REPO_SHA` pinned to its full base SHA, matching the existing canon-context
test contract. No `state/*`, `workspaces/*`, Kanban card, service, cron, account,
credential, marketplace, production prompt, spend, upload, or publication was
mutated by this implementation.

### Publication receipt

Draft PR #29 is open:

https://github.com/kopikonkf/income-os/pull/29

Initial remote implementation commit:
`0aa764d57edd6d61917634a4ff0a7fcb3590533e`. The PR targets `main` at
`d2c3e27a4c0d7affc4c9c82d5ef50d5d362446b6`; its nine-path manifest matches
the verified implementation tree. The PR is intentionally draft pending
Architect/Founder review and does not deploy or execute the runner.

OpenCode's independent Windows review found one test-only default-codec defect:
four `Path.read_text()` calls lacked an explicit encoding. Commit
`136b6f157d625346dffe4bc0fdd78656908f42cf` pins all four reads to UTF-8; no
production module changed. The independent Windows review worktree was
fast-forwarded to that commit and verified with `PYTHONUTF8` absent:

```text
python -m pytest bridge/tests -q: 182 passed
python bin/die_company_brain_check.py: PASS (7 identities / 6 runtime)
git diff --check: PASS
review worktree: clean
```

The Windows portability blocker is therefore closed. PR #29 remains clean and
ready for Founder merge review.

### Next controlled action

1. Complete Architect/Founder review of draft PR #29 and merge when approved.
2. After merge, fast-forward `C:\DIE` while preserving runtime-owned state and
   rerun the Windows suite.
3. Division-01 emits the exact executable Asset Blueprint plus Worth-Making
   receipt for the selected P0 family.
4. Founder reviews the derived plan and commits the bounded, expiring U1
   production authorization through State Manager.
5. Operator runs `m001_loop.py plan`; only after review, runs `materialize`.
6. Observe J2/J3 canary evidence before J4 can become eligible.
7. Founder keeps first marketplace submission manual and captures U2 receipts.

## Proactive Operator Layer v1 canon — 2026-08-24

### Baseline and verdict

- branch: `architect/proactive-operator-v1`;
- base: `main` at `0faace960dd4885758d7f0fed8f0c3b2d553de62`;
- verdict: **CANON DESIGNED / TESTED / NOT DEPLOYED**;
- runtime owner after merge: OpenCode integrator;
- mode: `PROPOSE_ONLY`, USD 0.00, committed M-001 scope only.

PR #29 proved autonomous dispatch after a J1-J8 graph exists. This revision
closes the preceding initiative gap: Hermes receives one bounded cognitive tick
that asks what can be worked now, selects one eligible transition, calls
Division-01 or creates/follows non-production cards, records learning, and
notifies Founder only for authorization, Founder QC, or CRITICAL containment.

### Canon decisions

- one prompt-based `die-proactive-operator-v1` cron is the cognition trigger;
  it is not a production cron, daemon, state store, or second control plane;
- V0 schedule is a `*/30 * * * *` observation hypothesis with no overlapping
  tick, 8-minute wall time, bounded context/output, one transition, maximum
  three mutations, and USD 0.00;
- every tick writes a `die.operator.tick.v1` receipt and one event through the
  existing `die_event.py`, including `NO_OP`;
- the ten-state machine is `IDLE`, `RESEARCH_PENDING`, `BLUEPRINT_PENDING`,
  `AWAITING_AUTHORIZATION`, `BATCH_RUNNING`, `QA_GATE`, `FOUNDER_QC`,
  `SUBMISSION_WAIT`, `LEARNING_LOOP`, and `TIER2_ROUTING`;
- Division-01 authors the exact prompt/variation plan; a Worker may serialize,
  validate, or execute the hash-pinned artifact but may not improvise it;
- ChatGPT image generation through Worker -> Proxima `:3211` remains the only
  production engine;
- `m001_loop.py` remains the only J1-J8 materializer and can be invoked only
  after the exact unexpired Founder `D-*` is committed;
- platform outcomes use route-specific `die.platform.receipt.v1` receipts;
  changed prompts require a new blueprint hash and new production authority;
- all-route rejection blocks scale and creates one Division-01 learning/
  revision request, not automatic regeneration; and
- Tier-2 is proposal-only because Pillar A remains `FUTURE`; rights/safety
  failures never enter social routing.

### Manifest and boundaries

The seven-path canon manifest is:

1. `ORCHESTRATOR_CONTRACT.md`;
2. `docs/operations/PROACTIVE_OPERATOR_V1.md`;
3. `company/schemas/die.operator.tick.v1.schema.json`;
4. `company/schemas/die.platform.receipt.v1.schema.json`;
5. `COMPANY_BRAIN.md`;
6. `IDENTITY/hermes-operator/AGENTS.md`; and
7. `bridge/tests/test_proactive_operator_canon_v1.py`.

The PR does not install/enable a cron, run an LLM, wake a principal, create a
card, mutate `state/*` or `workspaces/*`, change a profile/service/gateway,
produce an asset, spend, submit, publish, or create an account. Existing
deterministic crons and the live Gateway are untouched.

### Verification

```text
Targeted proactive canon regression: 11 passed
Full Linux bridge regression: 186 passed, 7 skipped
Windows bridge regression with PYTHONUTF8 absent: 193 passed
Company Brain validator: PASS (7 identities / 6 runtime identities)
Ruff: PASS
python -m py_compile: PASS
git diff --check: PASS
Windows review worktree: clean
```

Windows receipt was captured in the isolated
`C:\Users\aethers\AppData\Local\Temp\opencode\pr30` worktree at initial canon
commit `65afd07a8d45d690816626ba8ace446be2e0fad9`. Runtime-owned modifications in
`C:\DIE\state` remained preserved and outside the review worktree.

### Publication and next controlled action

Draft PR #30 is open:

https://github.com/kopikonkf/income-os/pull/30

Initial remote canon commit:
`65afd07a8d45d690816626ba8ace446be2e0fad9`. The PR targets `main` at
`0faace960dd4885758d7f0fed8f0c3b2d553de62`.

After Founder reviews and merges PR #30, OpenCode:

1. fast-forwards `C:\DIE` while preserving runtime-owned state;
2. implements a separate runtime PR for the bounded input projector, JSON
   validation, Division request/response capture, receipt/QC ingestion,
   prompt-based cron, and deterministic Founder-only pause/resume handler;
3. proves canon assimilation through principal-pinned `canon_context` rather
   than session memory or wake text;
4. runs S1 empty-state, S2 synthetic rejection, and S3 Tier-2 proposal
   simulations without touching live cards or production;
5. deploys V0 disabled, verifies the kill switch, then enables one bounded
   24-hour observation only after Founder authorization; and
6. captures the 24-hour zero-violation receipt for Founder promotion or repair.

Full mode, production expansion, submission, publication, account action, and
spend remain unauthorized.


---

## 2026-08-27 — MUXIA-B06 Linux checkpoint: MX-050 + GUI PASS

Authorized chain: sealed source preflight -> MX-050 headless -> restricted operator GUI -> MX-051 -> MX-052 -> STOP/evaluate.

Completed:

- sealed MUXIA source publication PASS on branch `architect/muxia-b06-linux-proof`;
- original source commit `1176c7a86ad369382e1aee23bdb7465a00c5de62`, 86-file manifest verified on Linux;
- MX-050 Linux runtime bootstrap DONE on Ubuntu 24.04.4;
- Node `v24.18.1`, Playwright `1.62.1`, Chromium `151.0.7922.34`;
- root-owned Playwright browser tree plus exact-path AppArmor `userns` profile; no `--no-sandbox`;
- Linux core regression 43/43 PASS; Linux parity 2 PASS + 3 explicit Windows-only evidence SKIP;
- Windows regression remains 48/48 PASS;
- XFCE+xrdp operator layer PASS and bound only to `127.0.0.1:3389`;
- MX-051 launcher installed at `/home/kopiko/Desktop/MUXIA-ChatGPT-Login.desktop`;
- dedicated profile `/var/lib/muxia/profiles/chatgpt-linux-a/browser` is mode 0700.

Repair:

- one child `MX-050-R1` absorbed the Linux bootstrap defects: undeclared TypeScript compiler, Ubuntu AppArmor userns restriction, and Windows-only physical parity evidence scope.
- no Electron dependency, credential read, protection bypass, or false success was introduced.

Current gate:

- `MX-051` is WAITING_FOUNDER_MANUAL_LOGIN.
- Founder opens the SSH tunnel, logs into XFCE as `kopiko` using the existing VPS password, launches `MUXIA ChatGPT Login`, authenticates manually, closes Chromium, then replies `LOGIN SELESAI`.
- Architect then resumes sanitized READY detection, text/image operator-controlled parity, restart proof, MX-052 four-profile isolation, and stops for receipt evaluation.

Still excluded: Executive, Division01, OAUTH, Atlas, Hermes production, Proxima, Aether, MCP Linux deployment, Cloudflare, marketplace submission/publication, spend, and cutover.


---

## 2026-08-27 — MUXIA-B06 authorized Linux scope complete

Authorized chain: sealed source preflight -> MX-050 headless -> restricted XFCE+xrdp GUI -> MX-051 single-profile parity -> MX-052 four-profile isolation -> STOP/evaluate.

### Canonical standing

- Publication branch: `architect/muxia-b06-linux-proof`.
- Windows `C:\DIE` remains the live reference and was not mutated by this migration proof.
- Linux source is `/srv/die/company/muxia`.
- Linux runtime is `/var/lib/muxia`.
- Node `v24.18.1`, Playwright `1.62.1`, and Chromium `151.0.7922.34` are verified.
- Root-owned Chromium plus exact-path AppArmor `userns` keeps the sandbox enabled; `--no-sandbox` was never used.
- XFCE+xrdp is tunnel-only at `127.0.0.1:3389`; no public RDP listener exists.
- `MX-050`, GUI layer, `MX-051`, and `MX-052` are `DONE / PASS`.
- `MX-060` and every later task remain `BLOCKED` pending separate Founder authorization.

### MX-051 receipt standing

- Founder completed manual login in dedicated profile `chatgpt-linux-a`.
- Sanitized state was `READY / COMPOSER_READY` before and after browser restart.
- Text canary response `MUXIA_LINUX_TEXT_OK_1` was confirmed by the Founder.
- Operator-downloaded image was registered as a durable PNG artifact:
  - bytes: 865,504;
  - SHA-256: `ae8717b508327af34ff00d7b820cf5764d689c2d2d9e8ee6909188bd8b7dc440`;
  - job status: `SUCCEEDED`.
- MUXIA read no credential, cookie, or token values and did not automate prompt submission or consumer-web output extraction.
- A headless protection challenge failed closed; the proof used the existing headed operator session without bypass.

### MX-052 receipt standing

- Four isolated Linux profiles B–E ran concurrently against a local synthetic origin.
- Unique ownership, duplicate-lease rejection, storage isolation, artifact/log lineage, and four successful jobs all passed.
- Captured envelope: 4,754,768 KiB aggregate RSS, 49 Chromium processes, 2,005 ms overlap.
- Teardown returned all four profiles to `READY`, cleared every lease/browser PID, and left zero residual B–E browser processes.
- Authenticated control profile A was excluded from the synthetic load.

### Verification and publication boundary

- Windows source regression: 54/54 PASS.
- Linux source regression: core 49/49 PASS; parity 2 PASS + 3 explicit Windows-only physical-evidence SKIP.
- Canonical receipts live under `company/muxia/receipts`.
- No merge to `main`, cutover, Linux MCP deployment, Executive/Division/Atlas/Hermes/Proxima change, Cloudflare action, marketplace action, spend, or production expansion was authorized or performed.

### Next controlled action

STOP and evaluate the MX-050 through MX-052 receipt package. Any work beginning with MX-060 requires a new explicit Founder authorization.

---

## 2026-08-27 — Chapter #4 Batch 7 PUB-001 revalidation

Founder authorized continuation from the B06 checkpoint through Linux canon/cutover gates, with Windows retained as rollback reference and `STOP_ON_FIRST_FAILURE` plus one repair child maximum per atomic task.

`PUB-001 — Revalidate B06`: PASS WITH ONE REPAIR CHILD.

Initial checkpoint verification:

- clean Windows publication staging: `b7d18d732974a4dc3e77df67a2afc2cfd8a721f9`;
- Linux `/srv/die`: same SHA and clean;
- remote feature branch: same SHA;
- `origin/main`: `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3`;
- feature branch was 19 commits ahead of main;
- no existing PR for `architect/muxia-b06-linux-proof`;
- B06 MX-050/GUI/MX-051/MX-052 receipts present;
- Windows regression: 54/54 PASS.

The first fresh-shell Linux revalidation failed 4 browser-launch tests with `CHROMIUM_DEBUG_PORT_TIMEOUT:30000`. Root cause was environment reproducibility, not browser-driver regression: a fresh shell did not inherit the B06-pinned `PLAYWRIGHT_BROWSERS_PATH=/opt/muxia/playwright-browsers`. Exactly one repair child, `PUB-001-R1`, added a Linux revalidation wrapper that pins the already-approved B06 environment without changing core driver or sandbox behavior.

Repair implementation commit: `2c7a1699fa1988c02f2c455b8c4e613db212db3e`.

Post-repair proof from canonical `/srv/die`:

- Linux build: PASS;
- Linux core: 49/49 PASS;
- Linux parity: 2 PASS + 3 Windows-only SKIP;
- `PUB001_LINUX_REVALIDATION_PASS` marker emitted;
- no second repair child;
- no merge to main, service migration, writer freeze, or cutover performed.

Durable receipt: `company/muxia/receipts/PUB-001-b06-revalidation.receipt.json`.

Next authorized task: `PUB-002 — PR and merge`, only after this receipt/handoff commit is pushed and Windows staging, remote feature branch, and Linux source are re-synchronized cleanly.

---

## 2026-08-27 - Chapter #4 PUB-002 GitHub publication merge

`PUB-002 - PR + exact changed-path review + merge if clean/green`: DONE / PASS.

Merge candidate `d6f330efd22bbf0b844be83ac028d8982c009675` was revalidated on both hosts before PR creation: Windows 54/54 PASS; Linux core 49/49 PASS plus parity 2 PASS / 3 explicit Windows-only SKIP / 0 FAIL. Exact changed-path review covered 112 files and found zero forbidden paths, zero `state/*` or `workspaces/*` runtime files, zero browser credential/session database files, and zero high-confidence secret hits. Six profile-named receipts flagged by a conservative filename heuristic were manually inspected and contained only sanitized metadata/synthetic markers, not credential values.

GitHub PR #32 `feat(muxia): publish Linux parity foundation B06` was created non-draft from `architect/muxia-b06-linux-proof` to `main`. GitHub reported `MERGEABLE / CLEAN`; no repository status checks were configured. Under Founder merge authorization, PR #32 was merged at `2026-08-27T18:58:22Z` with merge commit `c91f26cd5682de062c9ebb54b003ac8525ce8366`.

Durable receipt: `company/muxia/receipts/PUB-002-github-publication-merge.receipt.json`.

Publication is complete, but post-merge synchronization is intentionally not part of PUB-002. Linux `/srv/die` remains on the feature-branch checkpoint and live Windows `C:\DIE` remains on the pre-publication main/reference state until `PUB-003` performs controlled post-merge parity. No service migration, writer freeze, or cutover has started.

Next authorized task: `PUB-003 - Post-merge parity`.
---

## 2026-08-27 - Chapter #4 PUB-003 Post-merge parity

`PUB-003 - Post-merge parity`: DONE / PASS_WITH_ONE_REPAIR_CHILD.

Canonical GitHub `main` at parity proof was `4ea59ed2be338a6af0ece602b1a73fb042e584ea`. Clean Windows publication staging and Linux `/srv/die` were synchronized to that exact SHA using fast-forward-only operations. Live Windows `C:\DIE` was intentionally not reset, checked out, stashed, discarded, or fast-forwarded; its pre-PUB-003 observed state remained `main @ 04eda313f1e757c0d0f8fd9d90251b92c0dd95a3` with 37 dirty paths preserved as live rollback/reference state.

Post-merge regression against the exact canonical SHA passed on both hosts: Windows core 49/49 + parity 5/5 = 54/54 PASS; Linux build PASS, core 49/49 PASS, parity 2 PASS + 3 explicit Windows-only SKIP, 0 FAIL, with `PUB001_LINUX_REVALIDATION_PASS` emitted.

Rollback checkpoint tag `chapter4-pre-service-migration-20260827` was created and pushed at `4ea59ed2be338a6af0ece602b1a73fb042e584ea`. This is the stable pre-service-migration source anchor before any Architect MCP, Executive, Division01, Hermes/Worker, compatibility, or production cutover work.

Durable receipt: `company/muxia/receipts/PUB-003-post-merge-parity.receipt.json`.

Batch 7 publication is COMPLETE: PUB-001 PASS_WITH_ONE_REPAIR_CHILD; PUB-002 PASS/MERGED; PUB-003 PASS_WITH_ONE_REPAIR_CHILD. PUB-003-R1 was limited to final read-only rollback-tag verification and its evidence correction; no repository/runtime state mutation occurred. No service migration, writer freeze, Proxima cutover, or Windows DIE disablement has started.

Next eligible batch: `MUXIA Batch 8 - Windows estate and one-canon mapping`.
Next atomic task: `DIE-100 - read-only Windows estate inventory`.

---

## 2026-08-27 - Chapter #4 DIE-100 Windows estate inventory

`DIE-100 - read-only Windows estate inventory`: DONE / PASS_WITH_ONE_REPAIR_CHILD.

Inventory confirmed the Windows estate is not a single directory mirror. Live `C:\DIE` remains `main @ 04eda313f1e757c0d0f8fd9d90251b92c0dd95a3` with 37 dirty paths preserved and was not reset, checked out, stashed, discarded, or fast-forwarded. Clean publication/canon work continues from GitHub main via the staging clone.

Important estate facts: `C:\DIE\workspaces` is ~533.5 MiB and is not source-canon payload; `D:\object-asset-engine` is ~4.118 GiB dominated by live data/SQLite and has an active audit writer; `D:\V2 Proxima` is ~1.365 GiB dominated by `node_modules` and test userdata plus a separate ~645 MiB live browser profile; Hermes/BrowserClaw/Brave AppData roots are mutable runtime/profile state rather than source; `D:\Backup_VPS` is ~7.859 GiB archive estate; `D:\aether-bridge` remains protected external and unmodified.

Runtime topology was verified metadata-only: Proxima 3211/8501, Web-AI/OAUTH 8456, Architect MCP 8790, Executive/Division Runtime MCP 8791/8792, BrowserClaw 9010/9011/9110, Division01 Brave CDP 9333, plus protected Aether listeners. Executive/Division Runtime MCP Windows services remain running. No credential values, cookies, tokens, credential DB contents, or raw process arguments were read.

Founder ordering constraint is now carried forward: **Architect MCP Linux migration is deferred to the final pre-cutover stage** so the Windows Architect MCP remains the active bootstrap/control channel to the Windows VPS during the rest of the migration. The earlier roadmap ordering that placed Architect MCP Linux migration first is superseded and will be reflected formally in DIE-101/task-graph disposition.

Durable inventory: `docs/migration/DIE_WINDOWS_ESTATE_INVENTORY_V1.md`.
Receipt: `company/muxia/receipts/DIE-100-windows-estate-inventory.receipt.json`.

`DIE-100-R1` was the single repair child: metadata-only PowerShell queries were rewritten into PowerShell 5.1-compatible array-first form after parser failures that occurred before execution/mutation.

Next atomic task: `DIE-101 - disposition matrix`.
---

## 2026-08-27 - Chapter #4 DIE-101 Windows estate disposition matrix

`DIE-101 - disposition matrix`: DONE / PASS_WITH_ONE_REPAIR_CHILD.

DIE-100 inventory has been converted into an explicit source/data/runtime/provenance/external disposition canon. The allowed vocabulary is `MIGRATE_SOURCE | REBUILD_LINUX | MIGRATE_DATA | ARCHIVE_PROVENANCE | RETIRE_AFTER_CUTOVER | KEEP_EXTERNAL | UNRELATED_EXCLUDE`. A Windows root may have multiple dispositions because clean source, mutable data, runtime installation, credentials, and rollback evidence are separate migration units.

Key decisions are locked: live dirty `C:\DIE` is not a bulk-copy source; state migrates separately to `/var/lib/die`; `D:\object-asset-engine` source belongs under Atlas object-centric while its ~4.1 GiB data/SQLite remains mutable data with a consistent-snapshot requirement; Proxima remains provenance/rollback and is not imported into MUXIA; `D:\OAUTH` is its own Web-AI adapter under `company/next-subprojects`, not Division01; Aether estates are `KEEP_EXTERNAL`; browser profiles/credentials/caches are rebuilt or excluded rather than copied.

The one-canon mapping is now explicit for Architect, Executive, Atlas human/object, MUXIA, Division01, Hermes, Workers, and the Web-AI OAuth adapter. Source lives under `/srv/die`; mutable DIE data under `/var/lib/die`; MUXIA state under `/var/lib/muxia`; secrets/config under `/etc/die`; installed service builds under `/opt/die`.

Founder ordering constraint is now enforced in `company/muxia-task-graph-v1.json`: Windows Architect MCP remains active through `CUT-005`; `MX-053` is `DEFERRED` and depends on `CUT-005`; `MX-054` proves Linux Architect MCP without replacing the Windows control channel; actual Architect control handoff is explicit Founder task `CUT-006`. `MX-060` now also depends on `DIE-204`, so reliability work cannot bypass the one-canon/company topology migration.

Task-graph validation: 52 unique tasks, all dependencies resolve, no DAG cycle, `DIE-102` is the next READY task. `DIE-101-R1` corrected only the quoting of the final read-only Linux JSON verification after source sync; `python3 -m json.tool` then verified both canonical JSON files on Linux. No Windows runtime/service/data/profile mutation occurred during DIE-101.

Canonical matrix: `docs/migration/DIE_WINDOWS_ESTATE_DISPOSITION_MATRIX_V1.md`.
Receipt: `company/muxia/receipts/DIE-101-windows-estate-disposition-matrix.receipt.json`.

Next atomic task: `DIE-102 - env/path abstraction`.
---

## 2026-08-28 - Chapter #4 DIE-102 env/path abstraction

`DIE-102 - env/path abstraction`: DONE / PASS_WITH_ONE_REPAIR_CHILD.

DIE now has a canonical OS-neutral path contract at `company/contracts/die.path-roots.v1.json`. The five locked roots are `DIE_HOME`, `DIE_STATE_ROOT`, `MUXIA_ROOT`, `DIE_CONFIG_ROOT`, and `DIE_INSTALL_ROOT`. Windows defaults preserve the current `C:\DIE` deployment; Linux defaults resolve source to `/srv/die`, mutable DIE runtime/data to `/var/lib/die`, MUXIA runtime to `/var/lib/muxia`, protected config to `/etc/die`, and installed services to `/opt/die`.

Runtime-facing Python consumers were refactored so source/identity paths come from `DIE_HOME`, while State Manager, cron state, governed workspaces, Runtime MCP workspace/state boundaries, and M-001 loop state/workspaces resolve from `DIE_STATE_ROOT`. Runtime MCP no longer pins `PROJECT_ROOT = C:\DIE`; wrapper entrypoints no longer pin `C:\DIE\bin`. All configured roots must be absolute and relative roots fail closed.

Windows validation: targeted DIE-102 path tests 11/11 PASS; full bridge suite 204/204 PASS with `DIE_HOME` pointed at the clean staging repo and `DIE_STATE_ROOT` intentionally unset, proving the compatibility rule that Windows state inherits `DIE_HOME` unless explicitly separated.

Linux exact-commit proof used implementation SHA `2efad2d4e4f0e4cf8674352c9df8ea3f388a66d9`. Linux did not have pytest installed, so no package was added; stdlib assertions verified Windows defaults, all Linux defaults, relative-path rejection, and a clean worktree. Result: `LINUX_DIE102_PATH_PROOF=PASS`.

`DIE-102-R1` is the single repair child and covers execution/tooling harness corrections only: missing ripgrep fallback, a no-write patch-anchor mismatch, correction of an initially over-specified test environment and cleanup of its synthetic staging-only decision record, recovery of the implementation commit from local-main to the feature branch without changing origin/main, and SSH quoting replaced by `bash -s`. No live Windows service/state/profile/credential migration occurred.

Task graph now marks `DIE-102 = DONE` and `DIE-103 = READY`.

Architecture doc: `docs/architecture/DIE_PATH_ROOTS_V1.md`.
Receipt: `company/muxia/receipts/DIE-102-env-path-abstraction.receipt.json`.

Next atomic task: `DIE-103 - clean component import`.
DIE-102 publication proof: GitHub PR #39 merged at `1af7c2dab002e552fc9063539173b61f22386268`. Post-merge Windows bridge regression remained 204/204 PASS; Linux `/srv/die` was fast-forwarded cleanly to the same SHA and imported Linux defaults resolved to `/srv/die`, `/var/lib/die`, `/var/lib/muxia`, `/etc/die`, `/opt/die`. Live Windows `C:\DIE` guard remained `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3` with 37 dirty paths preserved.
---

## 2026-08-28 - Chapter #4 DIE-103 clean component import

`DIE-103 - clean component import`: DONE / PASS_WITH_ONE_REPAIR_CHILD.

The company topology is now materially represented under `company/` without creating duplicate active source trees. `company/component-registry-v1.json` records nine logical components. Executive, Division01, Hermes, and Workers are ownership boundaries over existing canonical repo paths pending their dedicated Linux migration tasks; MUXIA remains existing canon; Architect ownership is materialized but physical source/runtime import remains explicitly deferred to `CUT-005 -> MX-053`.

Human-centric Atlas moved through Git history to `company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md`; current operational references were updated and old operational-path reference count is zero.

Object Asset Engine was imported as a provenance-hashed Windows source snapshot under `company/atlas/object-centric/object-asset-engine/source-snapshot/windows-v1/`: 22 syntax-valid source files, no DB/data/state/config/cache. One upstream file, `scripts/audit/gemini_audit_parallel.py`, is syntax-invalid at source and is excluded with source hash/bytes recorded; no silent repair was made. Snapshot remains `linux_runnable=false` pending DIE-203 path/config refactor.

`D:\OAUTH` remains a separate next-subproject, not Division01. Only six tracked provider-neutral core files from Git HEAD `783c1e990c7f77ecdbf5bd2bab8c22be3cae2e49` were imported. Credentials, provider implementations, auth/token/PoW helpers, debug/live/network-capture scripts, server runtime, research/staging, logs, `.git`, and untracked plugins were excluded pending separate policy/runtime review.

Validation: Object provenance 22/22 PASS; OAUTH Git provenance 6/6 PASS; imported Python syntax 28/28 PASS; forbidden imported paths 0; high-confidence secret hits 0; full bridge regression 204/204 PASS. Linux exact implementation SHA `0eba02d772a3d19ab1a900d0cfc5c1b9427a2010` also passed component registry, Atlas canon, syntax 28/28, forbidden-path=0, clean worktree. Two non-fatal SyntaxWarnings from Windows-path docstrings confirm the object snapshot remains Windows-coupled until DIE-203.

`DIE-103-R1` is the single repair child covering null-safe scan correction, exclusion/provenance of the one upstream syntax-invalid source file, cleanup of test-created `__pycache__`, and CRLF-to-LF import normalization with separate source/imported SHA256 values. No live Windows service/state/database/profile/credential mutation occurred.

Canonical task doc: `docs/migration/DIE_CLEAN_COMPONENT_IMPORT_V1.md`.
Receipt: `company/muxia/receipts/DIE-103-clean-component-import.receipt.json`.
Task graph: `DIE-103=DONE`, `DIE-104=READY`.

Next atomic task: `DIE-104 - one-canon validator`.
DIE-103 publication proof: GitHub PR #41 merged at `2eea6f222f30635a77816dde4be089ecd83363d9`. Post-merge Windows bridge regression remained 204/204 PASS; Linux `/srv/die` was fast-forwarded cleanly to the same SHA and component/task/receipt/source-manifest JSON validated. Live Windows `C:\DIE` remained `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3` with 37 dirty paths preserved.
---

## 2026-08-28 - Chapter #4 DIE-104 one-canon validator

`DIE-104 - one-canon validator`: DONE / PASS_WITH_ONE_REPAIR_CHILD.

A stdlib-only fail-closed validator is now canonical at `company/scripts/validate_one_canon.py`, governed by `company/contracts/die.one-canon-validator.v1.json`. It performs 11 checks covering Git/canonical paths, component ownership, DIE-102 path-root separation, forbidden tracked company material, bounded legacy state, Architect/OAUTH/Aether boundaries, Atlas singular canon, Object/OAUTH snapshot integrity, and high-confidence secret tripwires.

The validator explicitly pins the 15 legacy tracked `state/` files that still exist from the Windows-era layout. That allowlist may not expand, tracked `workspaces/` remain forbidden, and the temporary exception must be removed only after `CUT-002/CUT-003` final state sync plus restore/replay proof.

`DIE-104-R1` is the single repair child. The first real validator run found stale Hermes component-registry refs to `bin/die_operator_tick.py` and `bin/die_operator_switch.py`; those files are absent from clean GitHub main. The registry was corrected to reference canonical SOUL/AGENTS plus shared bridge source, while live-only proactive-operator candidates are explicitly deferred to DIE-202 reconciliation. The same repair child also fixed an isolated negative-test importlib loader issue; no live runtime mutation occurred.

Validation evidence: targeted fail-closed suite 6/6 PASS, including intentional failures for tracked company credentials, new tracked runtime state, Architect ordering drift, and snapshot tamper. Full Windows bridge suite is 210/210 PASS. Exact implementation SHA `b4a2349b949555674c6246f8d6cb0661574220d0` passes the validator 11/11 with `--require-clean` on both Windows staging and Linux `/srv/die`; both worktrees were clean. Live Windows `C:\DIE` remains `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3` with 37 dirty paths preserved.

Task graph now marks `DIE-104=DONE`. `DIE-200`, `DIE-201`, `DIE-202`, and `DIE-203` are all dependency-eligible and marked `READY`; recommended next serial atomic task is `DIE-200 - Executive Linux migration`.

Architecture doc: `docs/architecture/DIE_ONE_CANON_VALIDATOR_V1.md`.
Receipt: `company/muxia/receipts/DIE-104-one-canon-validator.receipt.json`.

Next recommended atomic task: `DIE-200 - Executive Linux migration`.
DIE-104 publication proof: GitHub PR #43 merged at `66099c2503701018d354c6c1881c224665706ba6`. Post-merge Windows validator remained 11/11 PASS and full bridge regression remained 210/210 PASS; Linux `/srv/die` was fast-forwarded cleanly to the same SHA and validator remained 11/11 PASS with `--require-clean`. Live Windows `C:\DIE` remained `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3` with 37 dirty paths preserved.
---

## 2026-08-28 - Chapter #4 DIE-200 Executive Linux migration — WAITING_OPERATOR_AUTH

`DIE-200 - Executive Linux migration`: IN PROGRESS / WAITING_OPERATOR_AUTH.

Runtime implementation is staged at source SHA `26a27c1831710d773e7087eab0dd6de06e740c34`. Executive identity moved through Git history to `company/executive/IDENTITY.md`; identity registry, component registry, one-canon validator, and tests were updated atomically. Linux assets live under `company/executive/linux/`.

Linux Decision MCP is active as `die-executive-runtime-mcp.service` on loopback `127.0.0.1:8791`, principal `chatgpt-plus-executive`, 18 tools. Fresh Linux-only secrets are root-owned mode 0600 under `/etc/die/executive/runtime-mcp.env`. Service hardening includes dedicated user/group, `NoNewPrivileges`, `ProtectSystem=strict`, source read-only, state-only writable path, empty capabilities, and localhost-only network policy. Authenticated initialize/tools/system_health passed; unauthenticated MCP returned 401; journal secret-shape scan was zero.

`/var/lib/die/state` was bootstrapped only from clean Git-tracked state for pre-cutover proof, with SHA256 parity 15/15. This is not CUT-002 final state migration and no live dirty Windows state was copied.

The legacy Windows private-backend/Sentinel wake implementation was not ported. Linux consumer ChatGPT uses a fresh headed Playwright profile at `/var/lib/die/executive/browser-profile`, manual operator login only, and a non-sensitive heartbeat `/var/lib/die/executive/browser-status.json`. No cookie/token/profile clone, private backend, PoW/protection bypass, automated prompt submission, or output extraction is used.

Current heartbeat is `AUTH_REQUIRED` at `https://chatgpt.com/` with login UI present. This is expected negative proof that Windows session material was not cloned. The browser is already open in the Linux RDP desktop; DIE-200 cannot become DONE until Founder/operator login makes the heartbeat `READY`.

Windows rollback remains intact: `DIERuntimeMCPExecutive` Running/Auto on loopback 8791; live `C:\DIE` remains `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3` with 37 dirty paths. No public endpoint cutover occurred.

Validation so far: Executive targeted tests 6/6 PASS, full bridge 216/216 PASS, Windows one-canon 11/11 PASS, Linux one-canon 11/11 PASS. `DIE-200-R1` is the single repair child for shell transport/env quoting/readiness classification/identity-ref hygiene; no Windows production or credential mutation.

Task graph status: `DIE-200=WAITING_OPERATOR`. Do not start DIE-201 serially until the Executive auth gate closes.

Receipt: `company/muxia/receipts/DIE-200-executive-linux.receipt.json`.
Migration doc: `docs/migration/DIE_EXECUTIVE_LINUX_MIGRATION_V1.md`.
---

## 2026-08-28 - Chapter #4 DIE-201 Division01 Linux migration — WAITING_OPERATOR_AUTH

`DIE-201 - Division01 Linux migration`: IN PROGRESS / WAITING_OPERATOR_AUTH.

Division01 identity moved through Git history to `company/division/division001/IDENTITY.md`; registry/validator/tests were updated atomically. Linux assets are under `company/division/division001/linux/`.

Linux Decision MCP is active as `die-division01-runtime-mcp.service` on loopback `127.0.0.1:8792`, principal `division-head-division01`, 6 tools. Fresh Linux-only secrets are root-owned mode 0600 under `/etc/die/division01/runtime-mcp.env`. Authenticated initialize/tools/context_snapshot passed; unauthenticated MCP returned 401. Shared `/var/lib/die/state` ownership remained `die-executive:die-runtime` mode 770; DIE-201 did not take ownership or perform final CUT-002 state sync.

`D:\OAUTH` remains explicitly not Division01 and no OAUTH credential/auth/token/PoW/debug/browser state was imported.

The Windows private-backend/Sentinel wake implementation was not ported. Linux uses a fresh headed Playwright profile `/var/lib/die/division01/browser-profile` and non-sensitive heartbeat `/var/lib/die/division01/browser-status.json`, with manual operator login only and no cookie/token extraction, private backend, protection bypass, automated prompt submission, or output extraction.

Current Division01 heartbeat is `AUTH_REQUIRED`, expected for a fresh profile. Windows rollback remains active: `DIERuntimeMCPDivision01` Running/Auto, loopback 8792 and Brave/CDP 9333 listening. Live `C:\DIE` HEAD remains `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3`; dirty count was observed at 38 and is treated as dynamic while Windows writers remain active. No reset/discard/fast-forward/public endpoint cutover occurred.

Validation: targeted Division01 Linux tests 6/6 PASS, full bridge 222/222 PASS, Windows one-canon 11/11 PASS, Linux one-canon 11/11 PASS. `DIE-201-R1` is the single repair child for identity test refs, shared-state ownership guard, browser heartbeat schema, and shell/evidence hygiene.

Task graph status: `DIE-201=WAITING_OPERATOR`. Do not mark DONE until manual Linux login yields heartbeat `READY`.

Receipt: `company/muxia/receipts/DIE-201-division01-linux.receipt.json`.
Migration doc: `docs/migration/DIE_DIVISION01_LINUX_MIGRATION_V1.md`.
---

## 2026-08-28 - Chapter #4 DIE-202 Hermes + OpenCode Worker-001 Linux migration — WAITING_OPERATOR_CREDENTIALS

`DIE-202 - Hermes and Workers Linux migration`: implementation and Linux staging complete; external credential/channel activation remains deferred.

Role lock is canonical: Hermes = orchestrator; Worker = generic bounded executor; OpenCode CLI = Worker-001/default general execution worker V1; MUXIA = browser/provider/profile/job/artifact infrastructure; Architect MCP = DEV/control plane, not worker.

Hermes/Worker identity and contracts were materialized under `company/die-agents/hermes/` and `company/workers/`. Live-only Proactive Operator source (`die_operator_tick.py`, `die_operator_switch.py`, `die_platform_receipt.py`, runtime tests) was selectively reconciled from dirty `C:\DIE`, secret-scanned, refactored to DIE-102 path roots, and validated 11/11. No bulk dirty-tree copy occurred.

Linux OpenCode Worker-001 is installed at `/opt/die/workers/opencode`, package/functional version 1.18.23. Windows OpenCode config/provider credentials were not copied. DIE-202 invokes no model/provider call and no `opencode run`.

Linux Hermes is a clean upstream rebuild at `/opt/die/hermes/source`, exact commit `a0ca7c19204e514f9590ce3b812e029b315ab9e9`, functional version Hermes Agent v0.20.5 (2026.8.19), with fresh `HERMES_HOME=/var/lib/die/hermes/income-operator`. Windows `.env`, `auth.json`, `state.db`, sessions, caches, profile, and dirty Hermes checkout were not copied.

Hermes gateway service `die-hermes-gateway.service` is installed but disabled/inactive. `/etc/die/hermes/READY` is absent. `/etc/die/hermes/hermes.env` is root:root 0600 and contains only path bindings. This is intentional fail-closed behavior until fresh Linux provider/channel credentials are configured after Founder returns.

Actual Linux boundary proof as OS identity `die-hermes`: Hermes worker dispatch -> OpenCode 1.18.23 -> MUXIA JobRegistry/ArtifactRegistry -> `SUCCEEDED`; synthetic raster SHA256 `431ced6916a2a21a156e38701afe55bbd7f88969fbbfc56d7fe099d47f265460`; artifact/receipt/hash/bytes/MIME all PASS; provider call NO; consumer ChatGPT NO; spend USD 0. Shared workspace root `/var/lib/die/workspaces` is `root:die-runtime` mode 2770.

Final exact implementation SHA before publication evidence: `c6e26f7a39babb14c12613c30a6d98dd04db493b`. Final Windows full bridge 241/241 PASS with no staging-state mutation; Windows one-canon 11/11 PASS; Linux one-canon 11/11 PASS; Windows staging and Linux worktree clean.

Windows rollback/control remains intact: Executive and Division01 Runtime MCP services Running/Auto; listeners 8791/8792 and Division01 CDP 9333 active; Architect MCP 8790 active; live `C:\DIE` stays at `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3`, 38 dirty paths observed and untouched; Aether external/unmodified.

`DIE-202-R1` is the single repair child for provenance/tooling/install/test-isolation/ownership hygiene. No credential/profile migration or Windows production cutover occurred.

Task graph: `DIE-202=WAITING_OPERATOR_CREDENTIALS`. `DIE-203` remains READY independently because it depends on DIE-104, not on Hermes credential activation.

Receipt: `company/muxia/receipts/DIE-202-hermes-opencode-linux.receipt.json`.
Migration doc: `docs/migration/DIE_HERMES_OPENCODE_LINUX_MIGRATION_V1.md`.

NEXT ELIGIBLE: `DIE-203 — Atlas and Object Asset Engine Linux migration`.
---

## 2026-08-28 - Chapter #4 DIE-203 Atlas + Object Engine Linux migration — WAITING_OBJECT_FILTER_COMPLETION

`DIE-203 - Atlas and Object Asset Engine Linux migration`: Linux source/runtime/data baseline staged and verified; Windows Object Atlas remains authoritative while the 800k+ noun filtering/audit worker continues.

Human-Centric Atlas remains normative at `company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md`. Four Qwen Cross-Join/10D/validation documents were preserved byte-exact under `company/atlas/human-centric/foundations/qwen-crossjoin-v1/` as a non-normative foundation corpus. Promotion into canon requires Founder ratification. Preserved primitives include the 10D matrix, generative/contextual/commercial dimension classes, coherence constraints, weighted sampling, Opportunity/Worth-Making scoring, executable blueprint contracts, metadata/QA/platform routing, and event-driven scaling.

Object Engine Linux-ready source is canonical under `company/atlas/object-centric/object-asset-engine/source/`: 23 Python files, 0 pyc/pycache, 0 Windows object-engine or Dee_Workspace runtime path literals. `gemini_audit_parallel.py` remains excluded because the Windows source is syntax-invalid. Current `gemini_audit_scale.py` throttle drift (30s -> 5s) was reconciled before Linux path refactor.

Object runtime root: `/var/lib/die/atlas/object-asset-engine`, ownership `root:die-runtime`. Linux writer is NOT started. Gemini audit credential is not copied; Linux uses `DIE_OBJECT_ENGINE_GEMINI_KEY_FILE` and missing credential fails closed.

Consistent point-in-time SQLite baseline created through `sqlite3.Connection.backup` while Windows writer remained active. Main DB SHA256 `7a14ff13f4f1d2ea04b10ba84cb7774144313ef50bfa3cda3ec8fd1c8d407a00`, quick_check ok, candidate_seeds 714268, audit_queue 744259, pending 251294. Seed library SHA256 `b881e98eb604aad36ccf9eecac74d00a9afdb4b64dcc7f7fa30348451fea3ec2`, quick_check ok, objects 302134. Seven data files / 3,212,340,964 bytes passed SHA parity. Raw WAL/SHM were not copied.

Transfer used 27 bounded compressed chunks; 26/27 passed initially and one connection-closed chunk was retried exactly once. All chunk/archive hashes and post-extraction data hashes passed before promotion.

Implementation commit: `f0cb0a90de45ca155f1109ceb15721365a8d7488`. DIE-203 targeted tests 8/8 PASS; SQLite WAL backup fixture PASS; full bridge 249/249 PASS; one-canon 11/11 PASS; Linux source compile 23/23 PASS; credential fail-closed PASS; Linux runtime hash/count verifier PASS.

Windows Object Engine remains authoritative and active. Latest observed Windows DB state has advanced beyond the baseline: `object_asset_engine.db` 1,191,800,832 bytes and `seed_library.db` 47,919,104 bytes while `gemini_audit_scale.py --run` remains active. Live `C:\DIE` remains `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3` with 38 dirty paths observed and untouched.

Task graph: `DIE-203=WAITING_OBJECT_FILTER_COMPLETION`. Completion requires Founder report that filtering is complete, Windows writer quiesce, final SQLite refresh/delta, SHA/quick-check/critical-count parity, then explicit Linux authority promotion. Until then Linux baseline is consistent but stale-by-design.

Receipt: `company/muxia/receipts/DIE-203-atlas-object-linux.receipt.json`.
Migration doc: `docs/migration/DIE_ATLAS_OBJECT_ENGINE_LINUX_MIGRATION_V1.md`.

DIE-204 remains blocked because DIE-200/201 auth gates, DIE-202 credential gate, and DIE-203 final filter completion are still open.

DIE-203 publication: PR #48 merged at `5c080921158c8af4a4b804b5f2f952956f23d915`. Post-merge Windows bridge 249/249 PASS, Windows one-canon 11/11 PASS, Linux main one-canon 11/11 PASS, Linux Object runtime verifier PASS, and credential fail-closed PASS. Windows Object filtering worker remains authoritative/active; DIE-203 remains `WAITING_OBJECT_FILTER_COMPLETION`.

---

## 2026-08-29 - Atlas Opportunity Intelligence Foundation + Engine Audit v1

Audit scope: GitHub canon/main, live `C:\DIE`, Windows Object Asset Engine, and Hermes `income-operator` runtime/profile.

### Canonical findings

- Opportunity Signals Engine: **ABSENT**. No executable normalized platform/search signal collector exists yet.
- Demand Score Engine: **PARTIAL / HEURISTIC V0**. Object Engine `demand_score.py` is real code, but uses static priors/Qwen-era signal mapping and explicitly lacks live marketplace signal collection.
- Worth-Making Gate: **DOC + VALIDATOR ONLY**. Historical scorecards exist and `m001_loop.py` validates supplied score/veto/receipt fields, but no executable Worth-Making decision engine exists.
- Blueprint Engine: **ARTIFACT + VALIDATOR ONLY**. Historical `ASSET_BLUEPRINT.json` exists and was compiled by OpenCode; `m001_loop.py` validates/hash-locks an existing blueprint but does not author buyer thesis, master prompt, or semantic variation plan.
- Object Longtail Generator: **PARTIAL / CURATED V0**. `longtail_expand.py` has useful normalization/dedup/modifier/IP guardrails but expands only a small hard-coded seed dictionary; it is not yet a scalable cleaned-noun + Human-context + signal-driven engine.
- Hermes Proactive Operator: **ACTIVE / REAL**, but current V1 evidence model is not sufficient for the target engine graph. Cron `die-proactive-operator-v1` runs every 30 minutes using a profile-local `die_operator_prepare.py` wrapper that hardcodes `C:\DIE` and delegates to `C:\DIE\bin\die_operator_tick.py prepare`.

### Hermes loop gap

Current Operator V1 can infer cognition completion from legacy Kanban `done` cards and has no first-class receipts for Opportunity Signals, Demand Score, Division-01 Worth-Making, Executive review, Division-01 Blueprint authoring, or Executive Blueprint review. The runtime agent also supplies an `authority` label in each candidate action; finalization does not yet enforce a canonical fixed `action_type -> authority` map. Recent runtime history selected `CREATE_BLUEPRINT_COMPILE_CARD` based on legacy T1/T2/T2-R2 status. A Kanban `done` card is now explicitly non-authoritative for cognition gates.

Live Windows runtime was **not modified** by this foundation work.

### Canonical architecture locked

Human-Centric Atlas = demand generator.
Object-Centric Atlas = validated media-agnostic semantic primitive generator.
`OBJECT` in the 10D Human Atlas becomes a bounded queryable projection of cleaned Object Atlas, not a duplicated static mega-list.

Core equation:

`Object Primitive × Human Demand Context × Product Expression = Commercial Asset Hypothesis`

Cross-join is retrieval/constraint/weighted-expansion based; exhaustive Cartesian materialization is forbidden.

Product Expression is downstream and can range from primitive static assets through variants, compositions, packs/bundles, templates, motion/video, and 3D/spatial assets.

### Engine authority lock

- Division-01 = primary semantic AUTHOR of division-scoped Worth-Making and Blueprint semantics/master prompt.
- Executive = required second-line strategic reviewer for production-family promotion; returns NO_VETO / REVISE / VETO_PENDING_EVIDENCE / escalation, but does not edit the Division blueprint in place.
- Hermes = orchestrator/anti-macet only; routes requests/receipts, never authors Worth-Making judgment or prompt semantics.
- Worker/OpenCode = bounded collector/scorer/compiler/executor; may serialize/validate/hash but cannot invent missing commercial or prompt semantics.
- Founder = sovereign exact-hash production/spend/submission authority.

### Foundation/build targets

`OE-001` Opportunity Signals Contract + bounded collectors
`OE-002` Demand Score v1 consuming current signal receipts
`OE-003` Object Longtail v1 using cleaned seeds + Human modifiers + phrase-level signals
`OE-004` Worth-Making v1: deterministic precheck + Division AUTHOR + Executive review
`OE-005` Blueprint v1: Division AUTHOR + Executive review + deterministic compiler/hash lock
`OE-006` Hermes Operator v2: prerequisite receipts, deterministic authority map, canonical OS-neutral prepare wrapper, legacy-card quarantine
`OE-007` closed-loop canary through Founder exact-hash authorization and Worker/MUXIA

### New canonical documents

- `company/atlas/human-centric/CROSSJOIN_OBJECT_ATLAS_COMPLEMENT_V1.md`
- `docs/architecture/DIE_OPPORTUNITY_ENGINE_AUDIT_V1.md`
- `docs/architecture/DIE_OPPORTUNITY_ENGINE_ARCHITECTURE_V1.md`

Human Atlas canon now contains H6 dual-Atlas complement. Runtime canon projection includes the Cross-Join complement as a fourth required M-001 canon document for Division01 and Executive.

Validation on clean staging: targeted authority/projection/load suite 17/17 PASS; full bridge 254/254 PASS; one-canon 11/11 PASS.

NEXT BUILD RECOMMENDATION: `OE-001` first. Do not build Worth-Making/Blueprint automation on top of heuristic demand and legacy Kanban completion.

---

## 2026-08-29 - OE-000 Opportunity Intelligence atomic task-graph seal

`OE-000 = DONE`. The OE-001..OE-007 architecture is now materialized in `company/muxia-task-graph-v1.json` as 54 OE nodes total: one roadmap/authority seal, seven milestone gates, and their atomic implementation/canary children.

Only `OE-001A - Opportunity signal taxonomy and source classes` is `READY`; every downstream OE task is `BLOCKED` by explicit dependencies.

Execution batching is canonicalized in `docs/architecture/DIE_OPPORTUNITY_ENGINE_TASK_GRAPH_V1.md` as OE-B01..OE-B14. Batches reduce conversational overhead only; atomic acceptance, STOP_ON_FIRST_FAILURE, and one-minimal-repair-child discipline remain.

Critical dependency convergence is locked: OE-001 -> OE-002 -> OE-003 -> OE-004 -> OE-005 -> OE-006 may be built during the Windows overlap; `OE-007A` requires `OE-006 + DIE-204 + MX-070`. `MX-071` now explicitly depends on `OE-007`, so the Chapter #4 cutover path cannot bypass the governed intelligence closed loop.

Authority gates remain: Division01 = Worth-Making/Blueprint semantic AUTHOR; Executive = second-line strategic reviewer; Hermes = receipt-driven orchestrator only; Worker/OpenCode = bounded collector/scorer/compiler/executor; Founder = exact-hash production/spend/account/submission authority.

Validation: OE/task-graph + authority/runtime-context targeted suite 25/25 PASS; full bridge 262/262 PASS; one-canon 11/11 PASS.

Receipt: `company/muxia/receipts/OE-000-opportunity-engine-task-graph-seal.receipt.json`.

NEXT: execute `OE-B01` beginning at `OE-001A`; no additional roadmap design is required before OE-001 implementation.


---

## 2026-08-29 - OE-B01 Opportunity Signals contracts

`OE-001A`, `OE-001B`, and `OE-001C` are complete on the OE-001 branch: signal taxonomy/source classes, strict `die.division001.opportunity-signals.v1` receipt schema + semantic validator, and fail-closed acquisition/ToS boundary.

Opportunity Signal is explicitly evidence input only, not Demand Score, Worth-Making judgment, Blueprint decision, or production authority. Raw signal receipts permit only `OBSERVED`, `VERIFIED`, or `SYNTHETIC`; inference belongs downstream. UNKNOWN is never converted to zero.

Acquisition policy classes are `ALLOWED_BOUNDED`, `OPERATOR_REQUIRED`, `OFFICIAL_API_ONLY`, and `SYNTHETIC_ONLY`. Unknown policy is fail-closed. The contract forbids cookie/token extraction, private backend calls, CAPTCHA/protection/rate-limit bypass, stealth, unauthorized automation, and treating submission eligibility as collection permission.

No live collection, network request, platform login, credential use/copy, live `C:\DIE` mutation, or Object Atlas worker mutation occurred in OE-B01.

Validation: OE-B01 + graph targeted 21/21 PASS; full bridge 275/275 PASS; one-canon 11/11 PASS.

Task graph: `OE-001A/B/C = DONE`; `OE-001D` and `OE-001E = READY` in parallel; downstream remains blocked.

Receipt: `company/muxia/receipts/OE-B01-opportunity-signals-contracts.receipt.json`.

NEXT: OE-B02 ? implement two bounded fixture adapters, then normalized signal registry/dedupe/freshness and OE-001 acceptance regression.


---

## 2026-08-29 - OE-B02 / OE-001 Opportunity Signals Engine v1 acceptance

`OE-001 = DONE`. OE-B02 completed `OE-001D/E/F/G`: two deterministic source-shaped fixture adapters, SQLite signal registry with idempotent dedupe/conflict/freshness semantics, and the OE-001 regression/failure suite.

Fixture adapter A models a public-search UI supply observation (`ADOBE_STOCK`, `SEARCH_RESULTS_COUNT`); fixture adapter B models an approved official-API-style demand observation (`SEARCH_INTEREST_INDEX`). Both remain `SYNTHETIC` + `SYNTHETIC_ONLY`; no live source collection is claimed.

Registry proof: two independent receipts INSERTED; exact duplicate returns DUPLICATE and count remains 2; same dedupe identity with altered payload returns `E_DEDUPE_CONFLICT`; at a later evaluation time Adobe fixture is STALE while the longer-window API fixture remains FRESH. Current queries exclude stale evidence by default.

OE-001 acceptance explicitly proves the reusable evidence substrate only. It does not implement Demand Score, Worth-Making, Blueprint, or live-platform acquisition permission. Any live adapter requires a separately reviewed acquisition policy profile.

Validation: OE-001 contracts + engine + graph targeted 32/32 PASS; full bridge 286/286 PASS; one-canon 11/11 PASS; source bytecode artifacts 0.

Task graph: `OE-001A..G = DONE`, `OE-001 = DONE`, and `OE-002A = READY`.

Receipts: `company/muxia/receipts/OE-B02-opportunity-signals-engine.receipt.json` and `company/muxia/receipts/OE-001-opportunity-signals-v1.receipt.json`.

NEXT: OE-B03 ? OE-002A Demand Score schema/model versioning + OE-002B evidence normalization + OE-002C UNKNOWN/freshness policy.


---

## 2026-08-29 - OE-B03 Demand Score v1 contracts

`OE-002A/B/C = DONE`. Demand Score v1 now has a strict output schema, model ID/version/hash contract, explicit component-to-evidence mapping, and conservative UNKNOWN/freshness semantics.

Required components for a future `COMPLETE` numeric score are `external_demand`, `supply_competition`, and `commercial_intent`. Missing evidence is not zero. If one or more required components are missing/stale/rejected, v1 returns `PARTIAL` or `INSUFFICIENT_EVIDENCE` with `final_score=null`. A separate hard-veto artifact can force `HARD_VETO`, also with `final_score=null`.

Market observations must come from validated OE-001 Opportunity Signal receipts. Niche specificity, production feasibility, eligibility, and risk may use explicit deterministic/canon evidence but cannot masquerade as market demand. Default evidence reuse across multiple components is forbidden to prevent double counting.

The historical Object Engine `demand_score.py` is pinned only as `CALIBRATION_PROVENANCE_ONLY_NOT_PRODUCTION_TRUTH`; its fallback 0.30 values and static intent/trend/seasonality dictionaries are not production-v1 evidence.

No scoring weights or production arithmetic were assigned in OE-B03. All model components remain `UNASSIGNED_UNTIL_OE-002D`.

Validation: OE-002 contract + graph suite 24/24 PASS; full bridge 302/302 PASS; one-canon 11/11 PASS; bytecode artifacts 0.

Task graph: `OE-002A/B/C = DONE`; `OE-002D = READY`; OE-002E/F and milestone remain blocked.

Receipt: `company/muxia/receipts/OE-B03-demand-score-contracts.receipt.json`.

NEXT: OE-B04 ? implement deterministic scoring transforms/weights, calibration fixtures, ranking/regression, then OE-002 acceptance.


---

## 2026-08-29 - Production Assurance / QC Automation / Submission roadmap seal

QA, QC automation, platform submission, and full market-loop work are now first-class roadmap/task-graph families. 49 atomic nodes were added: QA-001, QC-001, common SUB-001, five marketplace adapters (Adobe Stock, Dreamstime, 123RF, Vecteezy, MotionElements), and CL-001 full market closed-loop canary. Magnific is explicitly excluded from marketplace adapters because it is a production/recovery service.

Audit truth: `bridge/income_os_bridge/m001_asset_qa.py` is an existing deterministic Universal QA core and will be promoted/refactored rather than rebuilt. Current M-001 submission still stops at `READY_FOR_MANUAL_SUBMISSION`; platform receipt ingestion exists but no Submission Engine exists yet. Founder remains manual QC authority today.

Founder-free QC is architecturally supported through SHADOW_ONLY -> CALIBRATED_RECOMMENDER -> BOUNDED_AUTO_QC -> SAMPLED_AUDIT. Automated QC cannot self-promote; removing mandatory Founder review from a bounded lane requires an explicit Founder-ratified delegation policy. QC delegation never implies submission delegation.

`OE-007` is now explicitly a governed production canary ending at first-class QA/QC feedback. `CL-001` is the full market closed-loop proof: QA -> QC -> authorized marketplace submission -> review receipt -> learning/ERVA feedback.

All new QA/QC/SUB/CL nodes are BLOCKED by upstream dependencies; current executable priority remains `OE-002D = READY`.

Validation: roadmap/task-graph targeted 17/17 PASS; full bridge 311/311 PASS; one-canon 11/11 PASS.

Receipt: `company/muxia/receipts/PAD-000-production-assurance-distribution-roadmap.receipt.json`.

NEXT remains OE-B04 / OE-002D deterministic scorer.


---

## 2026-08-29 - OE-B04 / OE-002 Demand Score Engine v1 acceptance

`OE-002 = DONE`. OE-B04 completed `OE-002D/E/F`: deterministic evidence-driven scoring, explicit versioned transforms/weights, 12-case calibration corpus, COMPLETE-only ranking, arithmetic revalidation, duplicate/conflict protection, same-source median aggregation, and deterministic replay.

Model `division001-demand-score-v1` is now `1.0.0`, contract SHA256 `d719c1376d9453724a53ec86caff49dd325337f549b3d90ce28c5b424490d442`. Non-risk weights sum to 1.0; required market components (`external_demand`, `supply_competition`, `commercial_intent`) carry 0.70 base weight. Known `risk_penalty` is a separate bounded `0.15 * penalty` deduction; hard veto remains outside numeric scoring.

Missing optional evidence is renormalized out of the weighted denominator and remains explicit UNKNOWN; it is never imputed to zero. Missing/stale required evidence, hard veto, or unknown veto clearance yields no numeric final score.

Pinned calibration: HIGH=0.821907, MEDIUM=0.613474, LOW=0.109096; same thesis lower-vs-higher supply=0.716357 vs 0.617330. Required-only evidence produces 0.672728 with LOW confidence and 0.70 known-weight coverage; explicit optional zero produces 0.470909, proving UNKNOWN != zero.

Legacy Object Engine Demand Score v0 remains calibration provenance only. Its missing-signal defaults (e.g. search=0.30, marketplace=0.30) are explicitly not production-v1 evidence.

Ranking only accepts COMPLETE numeric outputs; PARTIAL, INSUFFICIENT_EVIDENCE and HARD_VETO are deferred without artificial bottom scores. Exact duplicate evidence/scores collapse; conflicting identities fail closed; tampered final arithmetic is rejected.

Demand Score does not authorize production and does not replace Worth-Making/Executive/Founder/QA/QC/submission gates.

Validation: OE-002 engine/contracts + OE/PAD graph targeted 51/51 PASS; full bridge 329/329 PASS; one-canon 11/11 PASS; demand-score bytecode artifacts 0.

Receipts: `company/muxia/receipts/OE-B04-demand-score-engine.receipt.json` and `company/muxia/receipts/OE-002-demand-score-v1.receipt.json`.

Task graph: `OE-002A..F = DONE`, `OE-002 = DONE`, `OE-003A = READY`.

NEXT: OE-B05 — Longtail modifier ontology/phrase schema + Object Atlas cleaned-seed retrieval + Human Atlas demand-context retrieval.


---

## 2026-08-29 - OE-B05 Longtail retrieval foundation

`OE-003A/B/C = DONE`. Longtail v1 now has a typed 14-family modifier ontology, separate L0-L6 Product Expression axis, strict child-candidate schema, read-only approved Object Atlas seed retrieval, and bounded Human Atlas hypothesis-context retrieval.

Object retrieval uses SQLite read-only/query-only mode, exposes only bounded ID/name/object-class/category-prefix queries (max 50), does not duplicate the Object Atlas dataset, does not require final dataset immutability, and intentionally omits legacy `demand_score` from returned seed records.

Human Atlas context retrieval uses a small versioned canon-seeded registry (6 initial contexts), all labeled `HYPOTHESIS`; retrieval is compatibility ranking only, max 25, not market evidence, and never materializes the 10D Cartesian product.

Every future Longtail child candidate must state `evidence_state=REQUIRES_PHRASE_LEVEL_OE001_OE002` and `parent_demand.inherited_by_child=false`. Clean parent Object Atlas status or parent Demand Score never transfers demand to a child phrase.

Legacy `longtail_expand.py` guardrails remain salvage provenance (normalization, modifier classification, Jaccard near-dup, quota, IP recheck, idempotency), but its small hard-coded `EXPANSIONS` dictionary is not the v1 generation core.

Validation: OE-003 retrieval suite 12/12 PASS; OE/PAD graph combined 29/29 PASS; full bridge 341/341 PASS; one-canon 11/11 PASS; bytecode artifacts 0.

Receipt: `company/muxia/receipts/OE-B05-longtail-retrieval-foundation.receipt.json`.

Task graph: `OE-003A/B/C = DONE`; `OE-003D = READY`; OE-003E/F/G and OE-003 milestone remain blocked.

NEXT: OE-B06 — bounded dynamic expansion -> dedupe/IP/quota -> phrase-level signals/scoring -> persistence/ranking -> OE-003 acceptance.

---

## 2026-08-29 - OE-B06 / OE-003 Longtail Engine v1 acceptance

`OE-003 = DONE`. OE-B06 completed `OE-003D/E/F/G`: bounded deterministic Object+Human candidate generation, structural/IP/quota guardrails, child-specific OE-001 -> OE-002 evidence/scoring, separate idempotent Longtail persistence, and ACCEPTED+COMPLETE-only deterministic ranking.

Dynamic expansion no longer uses the legacy object-specific `EXPANSIONS` dictionary as its core strategy. Candidate IDs are deterministic over seed + Human context + normalized phrase + Product Expression. Parent demand inheritance remains forbidden.

Guardrails reject parent redundancy, exact duplicates, severe near-duplicates and quota overflow; moderate near-duplicates and high-confidence IP/trademark terms route to REVIEW rather than silent deletion. The IP list is explicitly protective/not complete legal clearance.

Phrase scoring validates exact child phrase, parent seed and parent candidate IDs through OE-001 validator/registry before OE-002. A cross-engine bug discovered during integration was fixed: OE-001 registry-only `registry_freshness` metadata is removed before passing strict canonical signal receipts to OE-002. Missing/stale required evidence still yields no numeric score; REVIEW candidates cannot be scored.

Longtail persistence uses a caller-supplied separate SQLite registry and never writes to Object Atlas DB. Exact replay is idempotent; conflicting candidate/score identity fails closed. Ranking includes only `guard=ACCEPTED + OE-002=COMPLETE + numeric final_score`; all other states remain deferred.

Synthetic no-network canary: 6 generated / 6 ACCEPTED. Three child phrases scored 0.815511, 0.584106, 0.137423 and rank in that order. First CLI run = 6 INSERTED + 3 ATTACHED; second run = 6 DUPLICATE + 3 DUPLICATE with identical ranking. Canary fixture SHA256 `6fff6ef22279bf5ba3d1fe02d1d0de949b44045005f339e72816f0a7f367466b`.

Validation: OE-003 engine 21/21 PASS; OE-001->OE-003 + OE/PAD graph 108/108 PASS; full bridge 362/362 PASS; one-canon 11/11 PASS; Longtail/Signals bytecode artifacts 0.

Receipts: `company/muxia/receipts/OE-B06-longtail-engine.receipt.json` and `company/muxia/receipts/OE-003-longtail-v1.receipt.json`.

Task graph: `OE-003A..G = DONE`, `OE-003 = DONE`, `OE-004A = READY`.

NEXT: OE-B07 — OE-004A deterministic Worth-Making precheck/hard vetoes -> OE-004B Division01 author contract -> OE-004C Executive review contract.

---

## 2026-08-29 - OE-B07 Worth-Making author/review contracts

`OE-004A/B/C = DONE`; `OE-004D = READY`; milestone `OE-004` remains BLOCKED pending OE-B08.

OE-004A now executes deterministic prerequisite/hard-veto checks only. It validates full Longtail candidate schema, exact guard candidate ID/hash binding, OE-002 semantic arithmetic/model integrity, score freshness and mandatory demand/supply/commercial-intent evidence, rights/IP, safety/deception, platform/Product Expression eligibility, production-tool rights, spend authorization semantics, and a structured falsifiable Human Atlas buyer/use-case hypothesis seed. Outputs are only PASS/BLOCKED/WAITING_EVIDENCE and `worth_making_semantics_authored=false`.

OE-004B seals principal `division-head-division01` as the sole Worth-Making semantic AUTHOR. Canon factor weights total 100; UNKNOWN factor score is null and never imputed to zero. Complete weighted totals enforce VALIDATE >=75, RESEARCH >=60, below 60 DEFER; conservative recommendations remain allowed. The artifact cannot grant production authority.

OE-004C seals principal `chatgpt-plus-executive` as `READ_ONLY_CHALLENGE` REVIEWER. Every review pins the exact Division artifact hash and must challenge six domains: evidence contradiction, score inflation/double counting, portfolio overlap, strategic opportunity cost, Product Expression fit, and hypotheses remaining. `NO_VETO` forbids material concern/unknown; REVISE/VETO_PENDING_EVIDENCE require explicit actions; Executive cannot edit the Division artifact or grant production authority.

Trust-boundary regression proves tampered OE-002 arithmetic and wrong Longtail candidate hash fail before cognition.

Validation: Worth-Making contracts 20/20 PASS; contracts + OE/PAD graph 37/37 PASS; full bridge 382/382 PASS; one-canon 11/11 PASS; bytecode artifacts 0. No live Division01/Executive cognition session, login, credential use, network acquisition, spend, Windows live DIE mutation, or Object writer mutation occurred in B07.

Receipt: `company/muxia/receipts/OE-B07-worth-making-contracts.receipt.json`.

NEXT: OE-B08 — OE-004D revision/return lineage -> OE-004E receipt principal/hash/freshness validator -> OE-004F governed pass/revise/veto/stale/forged-review suite -> OE-004 acceptance.


---

## 2026-08-29 - OE-B08 / OE-004 Worth-Making Gate v1 acceptance

`OE-004D/E/F = DONE`; milestone `OE-004 = DONE`; `OE-005A = READY`.

Immutable attempt lineage prevents review laundering: attempt N+1 may follow only REVISE/VETO_PENDING_EVIDENCE, must remain in the same chain, increment exactly once, pin the previous attempt hash/outcome, and use a new Division01-authored artifact ID/hash.

The governed bundle validator replays deterministic precheck from full source input, revalidates Division01 and Executive semantics, checks current Demand Score/hard-gate/Division/review freshness, repository SHA, principals, artifact hashes, and attempt lineage. Historical validity alone is insufficient.

Governed decisions: PROMOTABLE_TO_BLUEPRINT, RETURN_TO_DIVISION, WAITING_EVIDENCE, ESCALATE_FOUNDER, NOT_PROMOTABLE; invalid bundles fail closed. PROMOTABLE_TO_BLUEPRINT requires Division VALIDATE + Executive NO_VETO + current valid lineage and still grants no production authority.

Canary matrix PASS: PASS→Blueprint; REVISE→Division01; VETO→evidence collection; STALE/MISSING_PRINCIPAL/FORGED_REVIEW/KANBAN_ONLY→INVALID. Immutable revision N→N+1 proof PASS. Legacy Kanban `done` is not cognition proof.

Validation: governed-loop 11/11 PASS; OE-004 targeted+graph 48/48 PASS; full bridge 393/393 PASS; one-canon 11/11 PASS; bytecode 0. No live cognition login/call, network acquisition, credential use, spend, Windows live DIE mutation, Object writer mutation, or production authority expansion occurred.

Receipts: `company/muxia/receipts/OE-B08-worth-making-governed-loop.receipt.json` and `company/muxia/receipts/OE-004-worth-making-v1.receipt.json`.

NEXT: OE-B09 — OE-005A Division01 Blueprint authoring schema -> OE-005B Blueprint semantic validator/compiler boundary -> OE-005C Executive Blueprint review contract.


---

## 2026-08-29 - OE-B09 Blueprint AUTHOR / compile-boundary / REVIEW contracts

`OE-005A/B/C = DONE`; `OE-005D = READY`; milestone `OE-005` remains BLOCKED pending OE-B10.

OE-005A seals `division-head-division01` as Blueprint semantic AUTHOR. The Blueprint pins current governed Worth-Making, exact Division Worth-Making artifact, Executive Worth-Making review, and Longtail candidate. It preserves the accepted OE-004 candidate/family/commercial-use/differentiation/buyer-JTBD/buyer-utility/Product-Expression semantics while Division01 authors family thesis, visual constraints, exact master prompt, negative constraints, semantic variation plan, platform/metadata direction, QA/falsification, and economics hypotheses.

OE-005B validates semantic drift/completeness and creates a deterministic compile-input boundary only. The boundary re-runs validation itself, copies exact authored semantic fields, hashes every semantic field, fixes `semantic_content_mutated=false`, and permits only SERIALIZE_VALIDATE_HASH behavior. It is not the final compiler; no Founder-gatable compiled Blueprint hash exists yet.

OE-005C seals Executive as `READ_ONLY_CHALLENGE` reviewer of exact Blueprint + compile-boundary + governed Worth-Making hashes. Six required domains: Worth-Making thesis fidelity, family strategy coherence, constraint contradiction integrity, portfolio overlap/differentiation, Product Expression fit, and whether production actually tests the Worth-Making thesis. Executive cannot edit Blueprint semantics or grant production authority.

Validation: Blueprint contracts 14/14 PASS; contracts + OE/PAD graph 31/31 PASS; full bridge 407/407 PASS; one-canon 11/11 PASS; Blueprint bytecode artifacts 0. No live cognition call/login/credential/network/spend/runtime mutation or production authority expansion occurred.

Receipt: `company/muxia/receipts/OE-B09-blueprint-contracts.receipt.json`.

NEXT: OE-B10 — OE-005D final deterministic compiler -> OE-005E provenance/hash lock -> OE-005F failure/determinism suite -> OE-005 acceptance.


---

## 2026-08-29 - OE-B10 / OE-005 Blueprint Engine v1 acceptance

`OE-005D/E/F = DONE`; milestone `OE-005 = DONE`; `OE-006A = READY`.

The final Blueprint compiler is deterministic and canonical. It re-runs Division01 Blueprint semantic validation, reconstructs the compile boundary, requires an exact fresh Executive Blueprint `NO_VETO`, requires exactly one authored engine selection, validates the versioned MUXIA capability contract, copies exact authored semantics without mutation, and emits canonical JSON bytes.

Compiler capability contract v1 maps `MUXIA_CHATGPT_IMAGE` + `RASTER_IMAGE` to MUXIA provider `chatgpt` with required capability `image.generate`, supported raster MIME outputs, and pinned MUXIA contract evidence. This proves contract compatibility only; runtime login/profile/provider readiness is explicitly not claimed.

The hash-lock engine recompiles from full source lineage before locking, rejects noncanonical or forged compiled files, pins exact artifact bytes/SHA and semantic/capability provenance, and verifies post-lock integrity. `eligible_for_exact_hash_authorization=true` means the hash can be named in a later Founder decision; both `authorization_granted` and `production_authority_granted` remain false.

Synthetic compiler canary (not a live production Blueprint): SHA256 `f8b6de9eabea3a6fa78fe36b1b822b076d6ac13ffa1904fee9614b116a8a6829`, 7750 bytes, lock `BPLOCK-F8B6DE9EABEA3A6FA78F`, provider `chatgpt`, capability `image.generate`. Replay and lock verification PASS.

Failure/determinism regression covers ambiguous/unsupported/capability-mismatched engines, REVISE/stale review, semantic gaps, post-review mutation, noncanonical/forged compiled artifacts, post-lock artifact mutation and receipt hash tamper.

Validation: compiler suite 16/16 PASS; OE-005 contracts/compiler/graph 47/47 PASS; full bridge 423/423 PASS; one-canon 11/11 PASS; Blueprint bytecode artifacts 0. No live cognition, MUXIA provider invocation, runtime-readiness claim, credentials, spend, Windows live DIE mutation, Object writer mutation, or production authority expansion occurred.

Receipts: `company/muxia/receipts/OE-B10-blueprint-compiler.receipt.json` and `company/muxia/receipts/OE-005-blueprint-v1.receipt.json`.

NEXT: OE-B11 — OE-006A Operator v2 typed prerequisite receipt registry -> OE-006B deterministic action authority map -> OE-006C intelligence stage projection.


---

## 2026-08-30 - OE-B11 Operator v2 typed prerequisite/authority/stage foundation

`OE-006A/B/C = DONE`; `OE-006D = READY`; milestone `OE-006` remains BLOCKED pending runtime integration/quarantine/replay tasks.

Operator v2 now has an ordered typed prerequisite chain: Opportunity Signals -> Demand Score -> Division01 Worth-Making AUTHOR -> Executive Worth-Making review -> Division01 Blueprint AUTHOR -> Executive Blueprint review -> deterministic Blueprint compile/hash-lock -> exact Founder production authorization. Every observed receipt pins issuer, artifact schema/ID/SHA, validation proof, freshness and stage claims. Conflicting current receipts fail closed; stale receipts are incomplete; superseded history does not satisfy current progress.

Founder authorization is accepted only when its authorized compiled Blueprint SHA exactly matches the current hash-lock receipt and the decision is committed by `die-state-manager`. Kanban metadata is explicitly never cognition proof.

The canonical action map is default-deny with 26 actions. Authority classification is deterministic and cannot be supplied/overridden by a runtime model. Semantic requests are principal-pinned; Founder-required actions remain Founder-only; forbidden actions remain forbidden; `OP-INVOKE-M001-RUNNER` requires the complete typed chain plus exact Founder authorization.

The stage projector always selects the earliest missing typed receipt and emits `intelligence_stage`, `next_required_receipt`, `next_action_type`, required principal and action authority. Later receipts cannot skip a gap. Invalid chains project `BLOCKED_INVALID_RECEIPTS`; only a complete exact-hash-authorized chain projects `READY_FOR_PRODUCTION`.

Validation: foundation 20/20 PASS; foundation + OE/PAD graph 37/37 PASS; full bridge 443/443 PASS; one-canon 11/11 PASS; bytecode 0. No live `die_operator_tick.py`, Hermes cron, Kanban, cognition, credentials, network, spend or production authority were changed in OE-B11.

Receipt: `company/muxia/receipts/OE-B11-operator-v2-foundation.receipt.json`.

NEXT OE work: OE-B12 — OE-006D legacy Kanban cognition quarantine -> OE-006E canonical OS-neutral operator prepare entrypoint -> OE-006F anti-macet routing/follow-up.

Operational handoff after this batch: process pending Linux authentication/readiness for DIE-200/DIE-201 and audit the actual gates for DIE-203/DIE-204 without copying Windows credentials/profiles.


---

## 2026-08-30 - DIE-203 final Object Engine promotion

`DIE-203 = DONE`. Windows filtering completed naturally: 744,259/744,259 audit rows done; OBJECT 433,750, REJECT 295,676, UNSURE 14,833; worker process count 0.

Final quiesced main DB was verified and promoted to Linux: 1,210,871,808 bytes, SHA256 `e6e43fbd4bbee712de651c31a159bb66872a91b1b555f809d0177ba856eeb891`, quick_check ok, candidate_seeds 714,268, audit_queue/done 744,259/744,259.

Founder-approved `seed_library_final.db` is ratified as the final DIE-203 production baseline, replacing the 433,835-row checkpoint for runtime use. Linux canonical `seed_library.db`: 66,695,168 bytes, SHA256 `3035b179ba435a9cc4983ca567528b15941b1a9f205451d425cd40ce5925ab77`, quick_check ok, 475,560 rows, 475,560 distinct lower-trim words. Buckets: not_in_wordnet 401,121; wave3_eligible 41,725; h4_capital 32,542; eligible_control 172. The 433,835-row snapshot remains historical pre-Wave3 provenance.

Promotion was rollback-safe: old Linux runtime DB/WAL/SHM moved to `/var/lib/die/atlas/object-asset-engine/state/pre-die203-final-20260830T0929Z`; Windows source DBs were not overwritten/deleted; no Linux Object Engine writer was started.

Receipt: `company/muxia/receipts/DIE-203-final-promotion.receipt.json`. DIE-204 remains BLOCKED on DIE-200/DIE-201/DIE-202 completion.

---

## 2026-08-30 - DIE-200 / DIE-201 authenticated Linux READY closure

`DIE-200 = DONE` and `DIE-201 = DONE`. Founder completed manual authentication in the fresh Linux Executive and Division01 profiles. Canonical Linux operator launchers now direct-spawn standard Google Chrome Stable 152 with dedicated profiles and loopback-only ephemeral CDP observation; Playwright only attaches with `connectOverCDP` for non-sensitive READY classification. No Windows browser profile/session was cloned and no cookie/token/private-backend extraction, prompt submission, output extraction, Cloudflare bypass, UA spoofing or stealth was used.

READY proofs: Executive `chatgpt-plus-executive` at `https://chatgpt.com/`, editableCount 2, loginUiCount 0, Linux Runtime Decision MCP `127.0.0.1:8791` active with 18 tools. Division01 `division-head-division01` at `https://chatgpt.com/`, editableCount 2, loginUiCount 0, Linux Runtime Decision MCP `127.0.0.1:8792` active with 6 tools.

ChatGPT MCP connector endpoint handoff is intentionally separate from migration completion. Founder reports both ChatGPT connectors still target Windows. Roadmap now contains first-class `CUT-004A` Executive connector Windows->Linux and `CUT-004B` Division01 connector Windows->Linux, each requiring cloud E2E and Windows rollback retention until CUT-005. No connector was switched in DIE-200/201.

Windows rollback remains intact: Executive and Division01 Runtime MCP services Running/Automatic with listeners on 8791/8792; live `C:\DIE` remains untouched. DIE-202 remains `WAITING_OPERATOR_CREDENTIALS`; DIE-203 is DONE; therefore DIE-204 remains BLOCKED only by the remaining DIE-202 dependency among DIE-200..203.

Closure receipt: `company/muxia/receipts/DIE-200-201-auth-ready-closure.receipt.json`.

---

## 2026-08-30 - DIE-202 activation pre-inbound gate

DIE-202 credentials are configured and validated. Provider connectivity PASS; minimal Hermes inference canary returned `DIE202_PROVIDER_OK`. Telegram bot identity/home-chat reachability PASS and Hermes outbound Telegram canary PASS. `die-hermes-gateway.service` is enabled/active behind `/etc/die/hermes/READY`; canonical `TimeoutStopSec=45`. Journal high-confidence secret-shape hits: 0.

Task state is now `WAITING_OPERATOR_CHANNEL_CANARY`, not `WAITING_OPERATOR_CREDENTIALS`. The only remaining gate is a Founder-originated Telegram message `DIE202_TELEGRAM_INBOUND_OK` processed by the Linux gateway. No Windows Hermes auth/profile/state was copied or used. DIE-204 remains BLOCKED until that inbound canary closes DIE-202.


---

## 2026-08-30 - DIE-202 DONE + DIE-204 Linux company topology PASS

DIE-202 is DONE. Founder-originated Telegram input was persisted as Telegram/group `user` message state id 69 and produced the following Telegram/group `assistant` message state id 70 with exact marker `DIE202_TELEGRAM_INBOUND_OK`. Provider connectivity/inference, Telegram identity/home-chat reachability, Hermes outbound send, inbound routing/model response, active systemd gateway, READY gate, 45-second drain timeout, state quick-check, and zero high-confidence journal secret-shape hits all pass. Linux and Windows Hermes bots remain distinct identities; no cross-bot visibility is required and no Windows bot credential/profile/state was copied.

DIE-204 is DONE. Live Linux topology canary pinned Human Atlas SHA `3e011079...`, Object Atlas final baseline SHA `3035b179...` / 475,560 objects, Division01 live MCP 6 tools, Executive live MCP 18 tools, active Hermes gateway, OpenCode Worker-001 1.18.23, real `/var/lib/muxia` Job/Artifact Registry, and synthetic job `DIE204-topology-muxia`. MUXIA final status `SUCCEEDED`; verified 68-byte PNG artifact SHA `431ced6916a2a21a156e38701afe55bbd7f88969fbbfc56d7fe099d47f265460`; artifact/receipt/hash/bytes/MIME all PASS. No provider image call, production authority, submission, publication or spend occurred.

Aether boundary: active lineage text hits 0, protected symlink hits 0, no Aether dependency absorption. `company/architect` remains `DEFERRED_SOURCE_IMPORT`; Windows Architect MCP remains control/bootstrap through CUT-005. Only division001 is materially instantiated; division002..100 remain on-demand logical capacity rather than 99 dummy active source trees, consistent with DIE-103 one-canon materialization.

Task graph: DIE-200/DIE-201/DIE-202/DIE-203/DIE-204 all DONE. Validation: targeted 38/38 PASS; full bridge 459/459 PASS; one-canon 11/11 PASS; secret scan 0. Receipts: `DIE-202-final-activation.receipt.json` and `DIE-204-linux-company-topology.receipt.json`.


---

## 2026-08-30 - OE-B12 Operator v2 routing / prepare

`OE-006D = DONE`, `OE-006E = DONE`, `OE-006F = DONE`; `OE-006G = READY`. Legacy T1/T2/T2-R2 Kanban cards are quarantined as workflow metadata only and cannot satisfy cognitive gates. Canonical `bin/die_operator_prepare.py` is OS-neutral with `v1-compat` default and receipt-driven `--mode v2`; Windows and Linux executable smokes pass. Live Windows Hermes profile wrapper was replaced with the path-neutral delegate without modifying `C:\DIE` or the cron job definition; because the protected live old HEAD lacks the new entrypoint, it safely resolves the same workdir and falls back to existing `bin/die_operator_tick.py prepare`.

Anti-macet routing is deterministic: stable intent dedupe; duplicate OPEN intent before 30m -> observe/no-op; after 30m -> follow-up; after 3 dispatched follow-ups without progress -> block. Semantic requests are routed only to the pinned Division01/Executive principals; Founder production-auth draft is due only after compile-hash lock; runner invocation only after exact Founder authorization. Hermes authors no cognition semantics and gains no production authority.

Validation: focused 17/17 PASS; Operator foundation+routing+graph 45/45 PASS; full bridge 476/476 PASS; one-canon 11/11 PASS; secret scan 0. Windows canonical v2 smoke PASS; Linux canonical v2 smoke PASS from temporary branch worktree, which was removed with temporary state. Receipt: `company/muxia/receipts/OE-B12-operator-v2-routing.receipt.json`. Next: `OE-006G`.


---

## 2026-08-30 - OE-B13 / OE-006 Hermes Operator v2 acceptance

`OE-006G = DONE` and milestone `OE-006 = DONE`. Operator v2 is accepted as a receipt-driven anti-macet orchestrator with deterministic authority, OS-neutral prepare, legacy-Kanban cognition quarantine, principal-pinned semantic routing, and crash-safe replay. Hermes still authors no Division01/Executive semantics and gains no production authority.

The durable source of routing recovery is now the hash-chained `die.operator-v2.dispatch-journal.v1`. Every dispatch/follow-up/block claim is recorded atomically before an external side effect and pins the exact snapshot, typed receipt chain, routing plan, stage, action, target, counter and previous record hash. `routing-state.json` is a replaceable projection rebuilt from the journal.

OE-006G proves deterministic restart/replay, duplicate suppression, stale and forged receipt failure, legacy T1/T2/T2-R2 metadata-only replay, routing-state recovery, both plan/record crash windows, persistent follow-up counters, non-forgeable Founder gate, revocation of READY_FOR_PRODUCTION after authorization invalidation, tamper rejection, and terminal-block persistence.

Validation: focused OE-006+graph 69/69 PASS; full bridge 491/491 PASS; one-canon Windows 11/11 PASS; one-canon Linux 11/11 PASS; Linux-native replay/crash canary 11/11 PASS; changed-file high-confidence secret hits 0; tracked bytecode 0; diff check PASS. No live cron/service/Kanban/cognition/provider/submission/credential/spend or production-authority change occurred.

Receipts: `company/muxia/receipts/OE-B13-operator-v2-acceptance.receipt.json` and `company/muxia/receipts/OE-006-operator-v2-acceptance.receipt.json`.

NEXT runs in parallel: Lane A `MX-060 -> MX-061 -> MX-062 -> MX-070`; Lane B `QA-001A..F -> QA-001 -> QC-001A..G -> QC-001`. `OE-007` governed real-artifact canary starts after convergence. Windows live `C:\DIE` remains protected/dirty; Windows Architect MCP 8790 remains active through CUT-005; Linux `/srv/die` remains canonical main.


---

## 2026-08-30 - MX-B07 reliability pre-soak acceptance

`MX-060 = DONE`, `MX-061 = DONE`, and `MX-062 = READY`. MUXIA now exposes deterministic sanitized provider/profile/job/artifact health without profile/artifact paths, lease owner values, browser PIDs, raw exceptions, provider bodies, or session credentials. Recursive log sanitization redacts credential-equivalent keys and values and reduces errors to bounded diagnostic codes.

Fault injection proves deterministic timeout, dead-browser recovery, lease contention, invalid disk/artifact, and auth-required paths against the persistent registries. Every fault disposition has `successAllowed=false`; false success count is 0. Auth-required handling verifies the current lease owner, atomically persists `AUTH_REQUIRED`, clears PID/owner, increments failure count, and removes the lease; ambiguous owners fail closed without mutation.

Validation before publication: MUXIA TypeScript build/core/parity 64/64 PASS; standalone Windows full bridge 491/491 PASS; Windows one-canon 11/11 PASS; clean exact-source Linux one-canon 11/11 PASS; changed-file high-confidence secret hits 0.

Receipt: `company/muxia/receipts/MX-060-061-reliability-pre-soak.receipt.json`. Runtime boundaries held: no live `C:\DIE` or `/var/lib/muxia` mutation, provider call, credential read/copy, submission, spend, or production-authority expansion.

NEXT after merge: start the real elapsed 24-hour bounded non-production `MX-062` soak while `QA-001A..F -> QA-001 -> QC-001A..G -> QC-001` advances in parallel. A shortened duration cannot satisfy MX-062.

---

## 2026-08-30 - QA-B01 Asset QA promotion contracts

`QA-001A = DONE`, `QA-001B = DONE`; `QA-001C = READY` and `QA-001D = READY`. The existing deterministic M-001 raster QA core is promoted rather than replaced: workspace containment, SHA-256/raster integrity, lineage, format/dimension, rights, safety, watermark, exact-duplicate and review-required behavior remain explicit compatibility obligations.

First-class QA contracts now exist as `company/schemas/die.asset.qa.v1.schema.json` plus `company/contracts/die.asset.qa-taxonomy.v1.json`. The contract covers integrity, lineage, technical, rights, safety, watermark, duplicate, metadata/package, platform-profile-unknown and review-required states. HARD_VETO cannot be waived by QA; `REVIEW_REQUIRED` is never PASS. QA grants neither subjective aesthetic/commercial judgment nor submission/publication authority.

Implementation commit: `62bed28edbc834fe214f542b2884e227344c8266`. Validation: targeted QA/PAD/M-001 26/26 PASS; clean standalone full bridge 495/495 PASS; dedicated one-canon 6/6 PASS; one-canon validator 11/11 PASS; high-confidence company secret hits 0; generated bytecode 0; diff-check PASS.

Receipt: `company/muxia/receipts/QA-B01-asset-qa-promotion-contracts.receipt.json`.

Parallel standing point remains: `MX-062 = READY` for the real elapsed 24-hour bounded soak; `MX-070 = BLOCKED` on MX-062. NEXT assurance work: QA-B02, beginning with `QA-001C` reusable engine boundary and `QA-001D` dated platform-profile interface.


---

## 2026-08-30 - QA-B02 / QA-001 Asset QA v1 acceptance

`QA-001C = DONE`, `QA-001D = DONE`, `QA-001E = DONE`, `QA-001F = DONE`, and milestone `QA-001 = DONE`; `QC-001A = READY`. The reusable first-class Asset QA v1 boundary preserves deterministic M-001 universal QA behavior and adds dated, strict, fail-closed marketplace preflight profiles for Adobe Stock, Dreamstime, 123RF, Vecteezy and MotionElements. Magnific remains excluded because it is a production/recovery service rather than a licensing marketplace.

Platform requirements are explicitly `KNOWN` or `UNKNOWN`. An `UNKNOWN` requirement produces `PLATFORM_PROFILE_UNKNOWN_REQUIREMENT` as a hard veto and routes the package to `BLOCK_SUBMISSION`; QA never invents missing marketplace rules. Package preflight validates package/mission/batch/Blueprint/asset lineage, hashes, metadata, prepared-not-submitted state and known profile requirements while carrying `submission_authorized=false`. Subjective visual/aesthetic/commercial judgment remains QC scope and QA hard vetoes are not waivable here.

Implementation commit `8463749` was validated from a standalone clean clone before lifecycle transition: targeted QA/graph compatibility 34/34 PASS; MUXIA build/core/parity 64/64 PASS; full bridge 503/503 PASS; one-canon pytest 6/6 PASS; one-canon validator 11/11 PASS; high-confidence secret hits 0; bytecode 0; diff check PASS. Receipt: `company/muxia/receipts/QA-B02-asset-qa-engine-acceptance.receipt.json`.

MX lane remains unchanged: `MX-060/MX-061 = DONE`, `MX-062 = READY` for a real elapsed 24-hour bounded non-production soak, and `MX-070 = BLOCKED` on MX-062. Historical MX-062 runner text was not found in Windows branches, reflogs or dangling commits, so no unverified unpublished runner is treated as canon.

NEXT production-assurance task: `QC-001A` rubric/outcome/authority contract, then `QC-001B` Founder-labeled corpus and `QC-001C` bounded evaluator. `OE-007` remains blocked pending MX-070 and QC-001 convergence.


---

## 2026-08-30 - QC-B01 SHADOW QC foundation

`QC-001A = DONE`, `QC-001B = DONE`, `QC-001C = DONE`; `QC-001D = READY`. Asset QC v1 now has an explicit rubric/result/authority contract, Founder/manual label + corpus schemas, deterministic anti-cherry-pick sampling contract, and bounded SHADOW evaluator/CLI. The evaluator verifies QA/asset hash lineage, computes deterministic normalized score/confidence, returns PASS/REVIEW/FAIL recommendations, and forces `BLOCKED_BY_QA` when QA carries a hard veto or non-PASS route.

Authority remains unchanged: SHADOW recommendation is not Founder approval; release/submission/publication authority are false; QA hard vetoes are not waivable; no auto-QC delegation threshold is ratified. Corpus labels store bounded rationale summaries and immutable evidence/hash refs without requiring private reasoning.

Implementation commit was validated before lifecycle transition: targeted 17/17 PASS; MUXIA 64/64 PASS; full bridge 511/511 PASS; one-canon pytest 6/6 PASS; validator 11/11 PASS; secret scan 0; bytecode 0; diff check PASS. Receipt: `company/muxia/receipts/QC-B01-shadow-qc-foundation.receipt.json`.

NEXT: `QC-001D` calibration metrics -> `QC-001E` SHADOW dual-review/disagreement queue -> `QC-001F` versioned delegation policy (Founder ratification required) -> `QC-001G` replay/drift/audit -> QC-001 acceptance. MX-062 remains a real elapsed 24-hour gate and MX-070 remains blocked until it passes.


---

## 2026-08-30 - MX-062 runner readiness reconstructed

`MX-062 = READY`; `MX-070 = BLOCKED`. The previously non-durable soak-runner work described in the historical session has been reconstructed as a first-class restart-safe Git artifact. This readiness batch does **not** claim MX-062 completion.

The runner hard-codes a minimum real elapsed duration of 86,400,000 ms (24h), fixed 60-second sampling, >=95% expected-sample coverage, SHA-256 sample hash chaining, wall-clock/elapsed rollback rejection, tamper rejection and zero-tolerance failure counters. There is no duration/interval shortening flag. Each sample uses the actual persistent MUXIA Profile/Job/Artifact registries inside an isolated synthetic state root to prove duplicate lease rejection, dead-process recovery, durable artifact evidence before SUCCEEDED and persisted-state integrity. No provider, authenticated production browser profile, submission or spend authority is used.

Standalone validation pinned to implementation commit: MUXIA build/core/parity 70/70 PASS including MX-062 focused 6/6; full bridge 511/511 PASS; one-canon pytest 6/6 PASS; one-canon validator 11/11 PASS; high-confidence secret hits 0; bytecode 0; diff check PASS. Receipt: `company/muxia/receipts/MX-062-runner-readiness.receipt.json`.

NEXT MX lane: merge readiness -> Linux `/srv/die` pull -> build/install isolated `muxia-mx062-soak@<runtime-user>.service` -> explicit start -> real elapsed >=24h. Only a final receipt with >=95% coverage, zero failure counters and a valid chain may transition `MX-062 -> DONE` and `MX-070 -> READY`.


---

## 2026-08-31 - QC-B02 / QC-001 acceptance

`QC-001D = DONE`, `QC-001E = DONE`, `QC-001F = DONE`, `QC-001G = DONE`, and milestone `QC-001 = DONE`; `SUB-001A = READY`. Asset QC is now calibrated/shadow-capable and delegation-ready, but milestone completion does **not** remove Founder review. Canonical delegation remains `SHADOW_ONLY` with an unratified policy.

Calibration reports reproducibly measure agreement, false-pass, false-fail, hard-defect misses, confidence calibration, per-defect-class and per-asset-class performance. SHADOW dual review retains disagreements and low-confidence cases. Delegation modes are versioned as `SHADOW_ONLY`, `CALIBRATED_RECOMMENDER`, `BOUNDED_AUTO_QC`, and `SAMPLED_AUDIT`; every non-SHADOW release scope requires exact Founder ratification, policy-body hash, reviewer/model scope, asset-class/marketplace scope, validity window and calibration thresholds. `CALIBRATED_RECOMMENDER` still retains Founder-final authority.

Replay/drift audit is fail-closed: corpus/rubric mismatch, false-pass regression or hard-defect-miss regression blocks; noncritical agreement/confidence drift routes to review. QC never grants marketplace submission/publication authority, cannot waive QA hard vetoes and cannot self-promote its delegation mode.

Implementation commit `f65fccb6f1e3e342ce99da8c8419574893ff1545` was fully validated before lifecycle transition: focused QC assurance 27/27 PASS; MUXIA 70/70 PASS; full bridge 521/521 PASS; one-canon pytest 6/6 PASS; validator 11/11 PASS; secret scan 0; bytecode 0; diff check PASS. Receipts: `company/muxia/receipts/QC-B02-calibration-delegation-acceptance.receipt.json` and `company/muxia/receipts/QC-001-acceptance.receipt.json`.

MX convergence remains time-gated. The real Linux MX-062 soak started at `2026-08-30T17:18:02.696Z` from canonical Linux commit `dfb74d7e09b19f68381e1064899d70c645a61f26`; `MX-062 = READY` and `MX-070 = BLOCKED` until the real >=24h receipt proves >=95% coverage, zero failure counters and valid chain. GitHub main may advance with QC acceptance, but Linux `/srv/die` must remain pinned during the active soak.

NEXT convergence: close MX-062 only on real evidence -> `MX-070 = READY`; once MX-070 is accepted, OE-007 governed real-artifact canary may begin because QA/QC convergence is already satisfied. `SUB-001A = READY` is a separate submission-framework lane and carries no implicit marketplace-action authorization.


---

## 2026-08-31 - Linux principal MCP/identity roadmap canonized

Windows stable runtime was audited read-only before Linux identity/MCP work. `ID-LNX-000 = DONE`. Empirical baseline: Executive wake = BrowserOS neo/BrowserClaw CDP `:9110`, Runtime MCP `:8791`, 18 tools; Division01 wake = dedicated Brave CDP `:9333`, Runtime MCP `:8792`, 6 tools. Wake is outbound cognition transport with a persistent ChatGPT thread; Runtime MCP is the separate OAuth-protected state/decision line. Windows services/tunnel remain untouched.

Linux improvement doctrine: preserve those behavioral contracts while retaining isolated dynamic-CDP browser profiles, formal Division01 OE-001..OE-005 engine responsibilities, typed Executive review contracts, and Hermes Operator-v2 orchestration. Hermes must route cognition rather than absorb Division01/Executive work.

Immediate READY tasks: `MCP-LNX-001` isolated Executive/Division01 staging services and `ID-LNX-001` Hermes prompt-source convergence. Requested execution priority is MCP first. Staging DNS `executive-mcp.aethers.biz.id` and `division01-mcp.aethers.biz.id` exists; Cloudflare tunnel `linux-mcp` exists with no active connector; staging ports `8891/8892` were free.

Cutover safety is now explicit: `CUT-004A/B` must also wait for `MCP-LNX-005`; Windows remains rollback-capable through CUT-005. Architect remains last under existing `CUT-005 -> MX-053 -> MX-054 -> CUT-006` ordering.

MX-062 remains separately time-gated and immutable on Linux commit `dfb74d7e09b19f68381e1064899d70c645a61f26`; do not pull/rebuild/restart its source/service for this lane.

NEXT EXECUTION: `MCP-LNX-001` -> staging service validation; then `MCP-LNX-002` isolated tunnel; `MCP-LNX-003` E2E parity. Full graph: `docs/architecture/DIE_LINUX_PRINCIPAL_MCP_IDENTITY_ROADMAP_V1.md`.


---

## 2026-08-31 - MCP-LNX-001 implementation ready

`MCP-LNX-001` remains `READY`; implementation is complete but live staging has not yet been started. Implementation commit `55c7291` adds isolated Executive `:8891` and Division01 `:8892` Linux staging units, dedicated staging installers, and a server-pinned `staging-read-only` control policy. Tool discovery remains parity-compatible (Executive 18 / Division01 6), but control calls fail with `E_STAGING_READ_ONLY` before writer/state mutation. Systemd also exposes `/var/lib/die/state` read-only.

Staging source is intentionally separate at `/opt/die/staging/income-os`; active `/srv/die` is not pulled/rebuilt/restarted while MX-062 runs. Installers generate root-only staging OAuth/bearer material, validate `*.aethers.biz.id` origins, install units, and end disabled/stopped; no secret values are printed. Cloudflare remains out of scope until `MCP-LNX-002`.

Validation pinned to implementation: focused 6/6 PASS; bridge 531/531 PASS; one-canon pytest 6/6 PASS; validator 11/11 PASS; secret scan 0; bytecode 0; MUXIA build PASS. Receipt: `company/muxia/receipts/MCP-LNX-001-implementation-readiness.receipt.json`.

NEXT: publish implementation exact head -> isolated Linux source materialization -> install/verify staging units -> explicit local start -> health/401/tool/control-writer suppression checks. Only then may `MCP-LNX-001 = DONE` and `MCP-LNX-002 = READY`.


---

## 2026-08-31 - MCP-LNX-001 accepted live

`MCP-LNX-001 = DONE`; `MCP-LNX-002 = READY`. PR #81 implementation is deployed from isolated staging source `/opt/die/staging/income-os` at `f5eb7205b00e1c85da4213e1d6ed645766a9652e`. Active `/srv/die` remains clean/pinned at `dfb74d7e09b19f68381e1064899d70c645a61f26` for MX-062.

Executive staging: `die-executive-runtime-mcp-staging.service`, PID 228478, `127.0.0.1:8891`, 18 tools, `staging-read-only`, unauthenticated MCP = 401. Division01 staging: `die-division01-runtime-mcp-staging.service`, PID 228481, `127.0.0.1:8892`, 6 tools, `staging-read-only`, unauthenticated MCP = 401. Both are intentionally active but disabled (no boot persistence claim yet). Existing Linux 8791/8792 remain active.

No Cloudflare connector was started, no connector handoff occurred, no wake/browser path was exposed, no secret value was returned/read by Architect, and control mutation remains denied. MX-062 remains active with PID 200975. Receipt: `company/muxia/receipts/MCP-LNX-001-acceptance.receipt.json`.

NEXT: `MCP-LNX-002` activate isolated `linux-mcp` connector routing only `executive-mcp.aethers.biz.id -> 8891` and `division01-mcp.aethers.biz.id -> 8892`; never expose CDP/wake. Then `MCP-LNX-003` authenticated OAuth/principal/tool/context E2E.


---

## 2026-08-31 - MCP-LNX-002 implementation ready

`MCP-LNX-002` remains `READY`; implementation commit `66625fb` defines the isolated `linux-mcp` Cloudflare connector with exact ingress `executive-mcp.aethers.biz.id -> 127.0.0.1:8891`, `division01-mcp.aethers.biz.id -> 127.0.0.1:8892`, then terminal `404`. Architect MCP, CDP, browser/wake and Windows `*.aethers.web.id` routes are explicitly forbidden.

Tunnel token is outside repo/config/argv. systemd `LoadCredential=` presents an ephemeral credential file to unprivileged `die-cloudflared`; persistent token source is root-owned mode 0600. Installer requires the pre-provisioned token, validates exact ingress, installs the unit, and ends stopped/disabled.

Validation: focused 4/4 PASS; bridge 535/535 PASS; one-canon pytest 6/6 PASS; validator 11/11 PASS; secret scan 0; pyc 0; MUXIA build PASS. No connector activation or connector handoff claimed.

NEXT: publish exact head -> isolated MCP002 source checkout -> secret-preserving token provisioning -> install/verify stopped unit -> explicit start -> public health routing proof -> only then `MCP-LNX-002 = DONE`, `MCP-LNX-003 = READY`.


---

## 2026-08-31 - MCP-LNX-002 public Cloudflare acceptance

`MCP-LNX-002 = DONE`; `MCP-LNX-003 = READY`. Isolated tunnel `linux-mcp` (`32579323-1f96-4c0d-8aee-a03557c4a103`) is connected from Linux `157.20.32.166` through cloudflared 2026.8.2. Service `die-runtime-mcp-cloudflared.service` is active with PID 230828 and intentionally disabled at boot pending later stability/cutover work.

Public Executive proof: `https://executive-mcp.aethers.biz.id/health` = HTTP 200, principal `chatgpt-plus-executive`, 18 tools, `staging-read-only`; unauthenticated `/mcp` = HTTP 401 with principal-origin OAuth protected-resource metadata; OAuth issuer = exact staging domain. Public Division01 proof: `https://division01-mcp.aethers.biz.id/health` = HTTP 200, principal `division-head-division01`, 6 tools, `staging-read-only`; unauthenticated `/mcp` = HTTP 401; OAuth issuer = exact staging domain.

Ingress remains exactly two MCP origins plus terminal 404. No Architect/CDP/browser/wake/Windows `aethers.web.id` route is exposed. Tunnel token is root-only on Linux, never committed or returned. Windows tunnel remains untouched. MX-062 remains active on `/srv/die` SHA `dfb74d7e...`, PID 200975.

One edge nuance: Python `urllib` with its default client fingerprint was observed receiving 403 while curl receives the expected 200/401 behavior. This is not accepted as ChatGPT compatibility proof; `MCP-LNX-003` explicitly requires E2E installation/authentication from the real ChatGPT Executive and Division01 accounts.

NEXT: Founder installs the two staging MCP URLs in their corresponding ChatGPT accounts; prove OAuth login/registration, exact 18/6 tool discovery, principal pinning, `context_snapshot`, cross-principal isolation, and `E_STAGING_READ_ONLY` for control calls. Then `MCP-LNX-003 = DONE` and `WAKE-LNX-002` may advance once `WAKE-LNX-001` is also complete.


---

## 2026-08-31 - Two-company-instance re-key plan materialized

Founder direction accepted: DIE-WINDOWS and DIE-LINUX become sibling runtime company instances over one shared reviewed canon. Phase 1 isolates Executive and Division01 external cognition. Windows keeps `chatgpt-plus-executive` / `division-head-division01`; Linux receives `die-lnx-executive-001` / `die-lnx-division-001`. Shared role documents are NOT duplicated.

`COMPANY-INSTANCE-001 = DONE`, `IDENTITY-LNX-REKEY-001 = DONE`, `IDENTITY-LNX-REKEY-002 = DONE`, `IDENTITY-LNX-REKEY-003 = READY`, `IDENTITY-LNX-REKEY-004 = BLOCKED`. `MCP-LNX-003` is now BLOCKED on `IDENTITY-LNX-REKEY-004`; `WAKE-LNX-001` is also gated on the new-account login.

Phase-1 limitation is explicit: Hermes/worker logical principal namespaces remain transitional/shared identifiers, so full operational active-active company federation is NOT claimed. Shared-canon upgrades, not filesystem duplication, are the Linux-to-Windows convergence mechanism.

NEXT: implement/test runtime aliasing + instance-local escalation + staging unit re-key; deploy exact green head to Linux staging; prove public endpoints expose the new Linux principal IDs; then mark REKEY-003 DONE and REKEY-004 WAITING_OPERATOR_CREDENTIALS for Founder login.


Implementation readiness pinned at `294050a9b3569c7f3b2a7a47fd56a12a31a7150d`. Runtime MCP v1.2.0 supports both Windows and Linux instance principals; Linux principals map to the same shared semantic canon role profiles rather than duplicated identity documents. Instance-local escalation is enforced in both tool schema and validation.

Validation: MUXIA 70/70; bridge 544/544; one-canon pytest 6/6; validator 11/11; Company Brain PASS (9 identities / 8 runtime); secret scan 0; pyc 0. `IDENTITY-LNX-REKEY-003` remains READY; live staging still exposes the pre-rekey principal IDs until exact-head deployment. `IDENTITY-LNX-REKEY-004` remains blocked pending new-account login.


---

## 2026-08-31 - Linux company cognition principal re-key accepted

`IDENTITY-LNX-REKEY-003 = DONE`; `IDENTITY-LNX-REKEY-004 = WAITING_OPERATOR_CREDENTIALS`; `MCP-LNX-003 = BLOCKED` until the Founder logs NEW dedicated ChatGPT accounts into the existing Linux Executive and Division01 browser profiles.

Linux public MCP now exposes `die-lnx-executive-001` (18 tools, v1.2.0) and `die-lnx-division-001` (6 tools, v1.2.0) on `*.aethers.biz.id`. Windows `*.aethers.web.id` simultaneously remains `chatgpt-plus-executive` / `division-head-division01` (v1.1.0). This is the empirical phase-1 two-company cognitive-principal split.

During re-key the Linux staging bearer/login secrets were rotated, OAuth client IDs were re-keyed, and no secret value was returned. Authenticated local proof: both context snapshots bind to the new principals with canon-context VERIFIED; Division01 escalation targets only `die-lnx-executive-001` or Founder; cross-principal bearer use is denied 401; all control calls remain `E_STAGING_READ_ONLY`.

MX-062 remains active PID 200975 on `/srv/die` SHA `dfb74d7e...`. Cloudflare connector stayed active. Browser profiles were NOT logged out or changed. NEXT OPERATOR ACTION: login new dedicated Executive and Division01 ChatGPT accounts in Linux profiles; then mark REKEY-004 DONE and execute MCP-LNX-003 real ChatGPT E2E.


---

## 2026-08-31 - Executive Linux browser auth-profile repair staged

Founder observed OpenAI login route error `400 Invalid content type: text/html; charset=UTF-8` while attempting the NEW DIE-LINUX Executive account in the existing Executive browser profile. The browser engine is already the corrected direct-spawn Google Chrome Stable path; this recurrence is therefore treated as stale/pre-rekey auth profile state rather than a return to Playwright-launched Chromium.

Repair scope is Executive only. Canon launcher heartbeat principal is corrected from legacy Windows `chatgpt-plus-executive` to Linux `die-lnx-executive-001`. Live repair must stop only the Executive browser launcher, archive the old Executive profile without deleting it, create a fresh `/var/lib/die/executive/browser-profile`, and relaunch direct-spawn Chrome Stable using the Linux principal. Division01 and MX-062 remain untouched.


---

## 2026-08-31 - Division01 Linux browser principal rebind staged

After successful NEW Linux Executive login and monitored relaunch, the Executive heartbeat is `READY` on principal `die-lnx-executive-001` with direct-spawn Chrome Stable and dynamic loopback CDP. Division01 browser launcher is now being rebound from the Windows principal id to Linux `die-lnx-division-001`; the Windows Runtime MCP/identity bindings remain unchanged.


---

## 2026-08-31 - IDENTITY-LNX-REKEY-004 operator login gate closed

Founder completed manual login of both NEW dedicated DIE-LINUX ChatGPT accounts. Executive survives canonical relaunch as `die-lnx-executive-001`, heartbeat `READY`, Chrome PID 242302, dynamic loopback CDP `127.0.0.1:39353`. Division01 survives canonical relaunch as `die-lnx-division-001`, heartbeat `READY`, Chrome PID 243758, dynamic loopback CDP `127.0.0.1:42229`. No credential value was captured in canon and no Windows account/session was reused.

`IDENTITY-LNX-REKEY-004=DONE`. Dependency release: `MCP-LNX-003=READY` and `WAKE-LNX-001=READY`; `WAKE-LNX-002` remains BLOCKED pending both lines. MX-062 remains PID 200975 and production `/srv/die` remains pinned to `dfb74d7e...`.
