# Factory Asset V1 Job-Scoped Browser Lifecycle Contract

Status: **FA-337 DONE / PASS - contract only; runtime migration belongs to FA-338**
Date: 2026-09-17 WIB

## Boundary

FA-337 imports the **lifecycle semantics** proven by Factory Asset V2 H01-025/H01-026, not its product engine, profile identities, provider routing or SVG workflow. V1 remains the MUXIA/Hermes broad multi-variant production line. V2 remains the separate SVG/vector engine with `h01-web-pNNN` / `h01-web-sNN`.

FA-337 changes no live owner, systemd unit, browser profile, provider route or production process. FA-338 is the implementation task.

## Required V1 lifecycle

```text
queue/job
  -> scheduler admission + durable lease
  -> COLD persistent profile
  -> SPAWN_HEADFUL (one browser owner for this job)
  -> loopback CDP only
  -> live provider readiness
  -> exactly-once dispatch claim
  -> WORK
  -> durable terminal result
       OR durable COMMITTED_UNRESOLVED reconciliation state
  -> Browser.close
  -> prove browser root exited
  -> prove CDP disappeared
  -> release profile/browser lease
  -> COLD
```

A lightweight scheduler/broker process may remain resident. **Idle means zero governed browser roots, zero governed browser contexts and zero governed CDP listeners**, not necessarily zero control-plane processes. Persistent authenticated profile state remains on disk.

## Ownership invariants

1. One admitted V1 job owns one bounded headful browser instance. Concurrent jobs never share that browser.
2. One persistent profile has at most one automation owner or one Founder repair owner at a time.
3. Automated CDP is loopback-only and exists only for the bounded automated work phase.
4. Normal closure cannot precede a durable terminal result or a durable committed-unresolved reconciliation receipt.
5. Closure acceptance requires browser root exit, CDP disappearance and lease/mutex release.
6. Profile cookies, tokens, Local Storage, IndexedDB and other credential/session bytes are neither read nor copied by lifecycle machinery. Session persistence is obtained by reopening the same profile directory.
7. Existing V1 provider readiness, prompt, output-acquisition, lineage, Founder-QC and postproduction semantics remain intact.
8. Exactly-once dispatch truth dominates browser lifecycle. A committed provider request is never repeated merely because the browser later closes, crashes or encounters a protection page.

## Protection challenge / Founder repair

The Executive repair on 2026-09-16 confirmed the required pattern: authentication/protection recovery can succeed when the same persistent profile is opened headfully with CDP disabled, after which a later automation launch can reuse the authenticated session.

**Before dispatch:** protection/auth challenge is a pre-dispatch failure. Automation writes `AUTH_REPAIR_REQUIRED`, closes its CDP browser, releases browser ownership, and blocks that profile from automated work until Founder repair completes.

**After dispatch commit or when commit truth is uncertain:** automation must not retry. It writes durable `COMMITTED_UNRESOLVED`/reconciliation evidence first, then closes the browser. Existing FA-313 exactly-once/reconciliation rules continue to govern.

**Founder repair:** same persistent profile, headful browser, exclusive repair lease, **no CDP**. Automated dispatch is paused for that profile. Founder/platform flow may complete login/checkpoint/Cloudflare; the system never bypasses CAPTCHA or reads credential/session bytes. Founder closes/releases the repair browser before automation may reacquire the profile.

## Migration from current V1 owner model

Current V1 uses `external_chrome_owner.sh` plus attach-only broker semantics with `EXTERNAL_PERSISTENT_CHROME_CDP`. FA-338 must replace the browser ownership boundary without unnecessarily rewriting the scheduler/provider contracts.

The safe migration sequence is:

1. add a V1 job-browser runtime around the existing persistent V1 profile directories;
2. make browser spawn occur only after a governed scheduler lease/admission;
3. attach the existing provider worker to that job browser rather than to an always-on owner;
4. preserve live readiness immediately before dispatch;
5. preserve exactly-once dispatch/committed-unresolved behavior;
6. write lifecycle receipt and durable provider result before close;
7. close and prove process/CDP/lease release;
8. prove queue-empty state has zero governed V1 browser renderers;
9. prove a later job reopens the same profile with authentication still present without reading credential bytes;
10. only after bounded canary acceptance retire the persistent-owner startup path.

FA-339 separately assigns these headful windows to Founder-visible DISPLAY `:12` workspaces and formalizes interactive Founder handoff. FA-340 remains the filesystem-operability task.

## V2 evidence intentionally reused

H01-025 already proves: one runtime owner, one provider page, loopback CDP, durable terminal result before `Browser.close`, process/CDP disappearance and UDD-lock release. H01-026 proves durable scheduler lease + exactly-once dispatch claim and that persistent profile identity is distinct from active browser ownership.

FA-337 treats those as architecture evidence. It does **not** import V2 profile IDs, Brave fabric topology, SVG provider policy or H01 queue semantics into V1.

## FA-338 acceptance opened by this contract

FA-338 may start when implementation preserves every invariant above. Its critical acceptance sequence is:

```text
COLD -> SPAWN_HEADFUL -> WORK -> DURABLE_TERMINAL -> CLOSE -> COLD
```

with explicit alternate paths for `AUTH_REPAIR_REQUIRED` and `COMMITTED_UNRESOLVED`.
