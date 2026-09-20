# NexaBurst Architecture & Technical Operations Runbook V1

System: DIE H01 NexaBurst Object-Asset Engine  
Lane: WC-L0 — Soft Watercolor Clipart  
Host: H01 Linux (`die-prod-01`)  
Audience: Founder, ChatGPT Architect, OpenCode/Hermes operators

## 1. Scope

NexaBurst generates isolated commercial object assets from the Object Atlas reservoir.

Current production policy is intentionally narrow:

- one eligible noun
- one WC-L0 Watercolor manifestation
- deterministic typed prompt authority (`TYPED_VISUAL_CONTRACT_V1`)
- Nexa provider generation
- local V2 post-processing
- Founder QC state
- Telegram Vault backup verification

The Wave3 reservoir contains 42,667 WC-L0 candidate rows.

Completing the first-100 canary does **not** authorize full-reservoir production.

## 2. Production Pipeline

    Object Atlas / Wave3 reservoir
      -> manifestation ledger
      -> typed prompt compiler
      -> Phase-1 acquisition runner
      -> operator/browser/auth/Unlimited/disk gates
      -> Nexa provider job
      -> raw original + receipt
      -> V2 queue
      -> Factory V2 / RealESRGAN / deterministic QA
      -> WAITING_FOUNDER_QC
      -> Telegram Vault upload
      -> Telegram download-back SHA256 verification
      -> VAULT_VERIFIED

Founder control:

    Founder Telegram
      -> /nexa_status
      -> /nexa_pause
      -> /nexa_stop
      -> /nexa_resume
      -> /nexa_help
      -> nexaburst-telegram-control.service
      -> operator-control.json
      -> supervisor / runner / V2 / browser manager

## 3. Canonical Paths

Live session:

    /home/kopiko/die-sessions/NEXABURST-H01-P001/

Canonical Git worktree:

    /home/kopiko/die-sessions/NEXABURST-CANON-20260919/

Repo component:

    company/die-agents/hermes/production-runtime/nexaburst/
      bin/
      config/
      docs/
      systemd/

Durable runtime data:

    /var/lib/die/h01/nexaburst/
      profiles/
      raw/
      receipts/
      workspaces/
      state/
      vault/
      challenge/

Never store credentials, Telegram tokens, SSH private keys, browser cookies, or login secrets in Git.

## 4. Browser Runtime

Profile: nexaburst-p001  
UDD: /var/lib/die/h01/nexaburst/profiles/nexaburst-p001/udd  
CDP: 127.0.0.1:9311  
GUI: Display :12, Workspace 4

Scripts:

    bin/nexaburst-browser.sh
    bin/nexaburst-browser-manager.sh
    bin/nexaburst-health.mjs

Rules:

- one UDD owner only
- do not launch a competing browser while the UDD owner is alive
- PAUSED/STOPPED suppress automatic browser startup and age rotation
- RUNNING startup failures use cooldown, not a five-minute reopen loop
- browser rotation is deferred while a provider job is in flight
- normal steady state is one Nexa page

## 5. Provider Adapter

Script:

    bin/nexaburst-adapter.mjs

Responsibilities:

- connect to existing Brave via CDP
- verify authenticated Nexa session
- require active Unlimited
- submit through provider internal job API
- poll provider job
- download provider-original bytes
- SHA256 original
- write generation receipt
- enqueue V2

Never expose cookies, passwords, tokens, or browser credentials.

### Provider recovery rule

If a provider job is still processing after a polling window:

    save same job_id
      -> bounded backoff
      -> resume same job_id
      -> bounded poll windows
      -> BLOCKED + Founder alert if still non-terminal

Never submit a second provider job merely because an existing job is still processing.

A terminal provider failure may be retried only through the bounded retry policy.

## 6. Reservoir and Manifestation Ledger

Selector:

    bin/nexaburst-reservoir.py

Ledger:

    /var/lib/die/h01/nexaburst/state/nexaburst-manifestation-ledger.db

Primary identity:

    candidate_id + lane_id

Current lane:

    WC-L0

A noun is covered only when its manifestation reaches WAITING_FOUNDER_QC or VAULT_VERIFIED.

A submit attempt alone does not count as consumed.

## 7. First-100 Gate

Runner:

    bin/nexaburst-phase1-runner.py

Supervisor:

    bin/nexaburst-phase1-supervisor.sh

Current authorized scope:

    first 100 priority rows only

The supervisor is bounded to first-100. Candidate 101 must not start automatically.

Full 42,667 production requires separate Founder authorization.

Recommended future full-reservoir mode:

    100 items
      -> automatic health checkpoint
      -> continue if healthy
      -> auto-PAUSE + Founder alert on anomaly

This provides continuous operation without one unbounded multi-day loop.

## 8. Founder Operator Control

Durable state:

    /var/lib/die/h01/nexaburst/state/operator-control.json

### RUNNING

- allows only the currently authorized window
- still requires browser/auth/Unlimited/storage/technical gates
- does not unlock a larger production scope

### PAUSED

- no new provider submit
- current provider job may finish
- V2 may drain existing queue
- Vault may archive completed artifacts
- browser manager does not auto-open or rotate

Use for normal maintenance, provider instability, reboot, disk inspection, or manual QA.

### STOPPED

- no new provider submit
- V2 takes no new item after the current item finishes
- Vault remains available for already-completed artifacts
- browser manager does not auto-open or rotate

STOPPED is the emergency brake.

Do not kill an active RealESRGAN or provider job just to make a process list clean.

## 9. Telegram Founder Controls

Service:

    nexaburst-telegram-control.service

Script:

    bin/nexaburst-telegram-control.py

Commands:

    /nexa_status
    /nexa_pause [reason]
    /nexa_stop [reason]
    /nexa_resume [reason]
    /nexa_help

Mutation commands are accepted only from Telegram group creator/administrators.

Replies return to the topic where the command was issued.

Operational topic:

    5834

Vault topic:

    5842

Command audit:

    /var/lib/die/h01/nexaburst/state/telegram-control-audit.jsonl

If commands do not reply:

    systemctl status nexaburst-telegram-control.service
    sudo journalctl -u nexaburst-telegram-control.service -n 100 --no-pager
    tail -100 /var/lib/die/h01/nexaburst/state/telegram-control-audit.jsonl

Do not print the bot token.

## 10. V2 Post-Processing

Worker:

    bin/nexaburst-v2-worker.py

Queue:

    /var/lib/die/h01/nexaburst/state/v2-queue.jsonl

Completion:

    /var/lib/die/h01/nexaburst/state/v2-done.jsonl

V2 performs local Factory post-processing including CPU RealESRGAN.

Retry policy:

- first recoverable failure: bounded retry
- source-lineage mismatch: HOLD
- repeated deterministic failure: HOLD + Founder notification
- storage gate: pause V2 and stop raw backlog growth
- STOPPED: do not take new V2 work

## 11. Telegram Vault

Script:

    bin/nexaburst-vault.py

Verification flow:

    build ZIP
      -> SHA256 local archive
      -> sendDocument
      -> getFile
      -> stream download
      -> SHA256 restored bytes
      -> compare byte count + hash
      -> BACKUP_VERIFIED
      -> delete temporary local ZIP

Upload success alone is not backup success.

Transport failures are bounded. Deterministic config/size/hash failures are held.

## 12. Storage

After the 2026-09-20 provider expansion:

    /dev/sda     about 640 GB
    /dev/sda2    ext4 root
    usable root  about 629 GB

The provider expanded the existing primary disk. It did not attach a second data disk.

Therefore:

- do not format anything
- do not create a new filesystem
- do not migrate NexaBurst paths
- do not alter mounts just because capacity increased

Always inspect:

    lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL
    df -hT
    blkid
    findmnt

## 13. SSH and RDP Baseline

Mission Control SSH target:

    target: die-prod-01
    user: kopiko
    public NAT port: 25013

Guest sshd remains on port 22.

kopiko baseline:

- shell /bin/bash
- public-key auth enabled
- password auth enabled
- TCP forwarding enabled
- sudo retained
- no chroot
- no ForceCommand
- no kopiko-specific Match restriction
- no global AllowUsers restriction limiting normal access

XRDP:

    127.0.0.1:3389
    Display :12

Founder Windows tunnel:

    ssh -N -o PreferredAuthentications=password -o PubkeyAuthentication=no -o ExitOnForwardFailure=yes -L 13389:127.0.0.1:3389 -p 25013 kopiko@157.20.32.166

Then RDP to:

    127.0.0.1:13389

## 14. H01 Public Ingress

Cloudflare tunnel service:

    die-runtime-mcp-cloudflared.service

Local origins:

    Executive staging read-only  -> 127.0.0.1:8891
    Division01 staging read-only -> 127.0.0.1:8892
    Architect H01 MCP            -> 127.0.0.1:8890
    OpenCode H01                 -> 127.0.0.1:3000

Public routes:

    https://executive-h01-mcp.aethers.web.id
    https://division01-h01-mcp.aethers.web.id
    https://architect-h01-mcp.aethers.web.id
    https://opencode-h01.aethers.web.id

Expected external checks from Windows Office:

- Architect /health -> HTTP 200
- Executive /health -> HTTP 200
- Division01 /health -> HTTP 200
- OpenCode root without credentials -> HTTP 401, proving route + Basic Auth

After the 2026-09-20 recovery, both staging MCP services and the tunnel service are enabled at boot.

Public ingress health and Mission Control health are separate signals.

## 15. Mission Control Relationship

Mission Control runs on Windows Office.

H01 principals use:

    remote_runtime_target = die-prod-01

A Cloudflare 1033/530 on H01 does not automatically mean Mission Control is dead.

Check separately:

1. Windows Office Mission Control health
2. SSH broker die-prod-01
3. H01 principal remote_broker_state
4. H01 public Cloudflare ingress

Do not collapse these into one health signal.

## 16. Standard Operator Checks

Overall:

    /home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-control.py status

Provider/browser:

    node /home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-health.mjs

Reservoir:

    /home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-reservoir.py stats

Processes:

    pgrep -af 'nexaburst|realesrgan|brave.*nexaburst-p001'

Disk:

    df -h /var/lib/die/h01/nexaburst

Cloudflare:

    systemctl status die-runtime-mcp-cloudflared.service
    sudo journalctl -u die-runtime-mcp-cloudflared.service -n 100 --no-pager

## 17. Incident Procedure

1. Brake production with /nexa_pause.
2. Use /nexa_stop for severe maintenance.
3. If Telegram is unavailable but SSH works, set PAUSED with nexaburst-control.py.
4. Inspect provider inflight, RealESRGAN, disk, browser/CDP, auth/Unlimited, V2, Vault, SSH/RDP, Cloudflare and Mission Control.
5. Preserve active atomic work.
6. Repair only the failing layer.
7. Validate objective evidence.
8. Explicitly resume only the currently authorized window.

Examples:

- disk expansion: inspect first; never format blindly
- CDP failure: check UDD owner before browser restart
- Cloudflare 1033/530: test origin and tunnel independently
- provider processing timeout: resume same job_id
- Vault transport error: retry Vault, not generation

## 18. What OpenCode Must Never Do

OpenCode or Hermes must not:

- unlock full 42,667 production without explicit Founder authorization
- clear Founder PAUSED/STOPPED state on its own
- delete the manifestation ledger
- reset completed state to force regeneration
- submit a second provider job while an old job_id is non-terminal
- format or repartition storage without explicit Founder authorization
- expose Telegram token, SSH private key, cookie, password, or session secret
- disable Vault download-back hash verification
- mass-kill Brave by generic process name
- kill unrelated browser profiles
- convert deterministic lineage errors into silent retry
- bypass WAITING_FOUNDER_QC

## 19. OpenCode Recovery Handoff

When Founder asks OpenCode to diagnose NexaBurst:

1. Read this file first.
2. Run nexaburst-control.py status.
3. If uncertain, PAUSE before changing anything.
4. Confirm current authorized scope.
5. Inspect active provider/V2 atomic work.
6. Inspect durable control and ledger state.
7. Repair only the failing layer.
8. Validate syntax/configuration.
9. Prove health.
10. Report exact files/services changed.
11. Leave PAUSED unless Founder explicitly asked to resume.

Minimum report:

    NEXABURST_RECOVERY_REPORT
    control_mode=
    authorized_window=
    nexa_authenticated=
    unlimited_active=
    browser_cdp=
    nexa_tab_count=
    provider_inflight=
    v2_active=
    v2_backlog=
    vault_backlog=
    first100_complete=
    first100_failed=
    disk_free=
    mission_remote_broker=
    cloudflare_ingress=
    changes_made=
    safe_to_resume=YES/NO

## 20. Core Operational Principle

NexaBurst must never turn infrastructure uncertainty into more production activity.

Default incident behavior:

    uncertainty
      -> stop admitting new work
      -> preserve current atomic work
      -> gather evidence
      -> notify Founder
      -> repair
      -> verify
      -> explicit resume

That rule takes precedence over throughput.
