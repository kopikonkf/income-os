# FA-339 — Founder-visible DISPLAY :12 workspace and interactive handoff

Status: **DONE / PASS**  
Date: 2026-09-18

FA-339 moves the current V1 production and cognition browser operating surface from hidden per-runtime Xvfb displays to the persistent Founder XFCE session on `DISPLAY=:12.0`, while preserving FA-338 demand-driven browser ownership. Persistent browser profiles remain durable on disk; browser processes remain job-scoped and return to COLD after terminal evidence.

## Canonical workspace mapping

```text
Workspace 1 -> Founder/general desktop
Workspace 2 -> Executive cognition
Workspace 3 -> Division01 cognition
Workspace 4 -> V1 Runtime 01
Workspace 5 -> V1 Runtime 02
```

Automation places browser windows by the actual browser-process tree, not by title. The browser-owning services share the host X11 socket and expose no public CDP endpoint. CDP remains loopback-only and exists only during the bounded automated work phase.

## Interactive Founder handoff

Founder handoff is safe preemption, not an unsafe hard kill:

```text
automation WORK
  -> Founder requests handoff
  -> durable ACTIVE hold blocks new admission immediately
  -> any already-committed job drains to durable terminal
  -> automated browser closes and returns COLD
  -> same persistent profile opens headful with CDP disabled
  -> Founder owns the profile exclusively on its dedicated workspace
  -> Founder closes/releases browser
  -> hold becomes CLOSED
  -> automation may admit a new job again
```

The handoff process detector reads `/proc/<pid>/cmdline` and only accepts actual Chrome/Chromium/Brave executables with an exact `--user-data-dir=<profile>` argument. Shell commands that merely mention a profile path cannot falsely claim ownership.

## Live acceptance

### Cognition visibility

- Executive visible canary opened on Workspace 2 and returned COLD with no forced cleanup.
- Division01 visible canary opened on Workspace 3 and returned COLD with no forced cleanup.
- Real post-cutover production cognition for `PRODSEED000138` also completed on the visible surface:
  - Division01 author `COG-PROD_BP_AUTHOR_PRODSEED000138_R01` completed in Workspace 3.
  - Executive review `COG-PROD_BP_REVIEW_PRODSEED000138_R00` completed in Workspace 2 with `NO_VETO`.
  - Card advanced to `BLUEPRINT_READY`.
  - Both principal profiles returned COLD.

### V1 production visibility

V1 Runtime 02 visible canary opened on Workspace 5 and closed back to COLD with:

- browser process gone,
- loopback debug endpoint closed,
- broker control endpoint closed,
- runtime lease released.

### Founder handoff

A bounded Runtime 02 handoff proved:

- ACTIVE handoff hold was written before Founder ownership,
- a new automated admission was rejected with `E_FOUNDER_HANDOFF_HELD:cluster-b`,
- the already-running synthetic automation job drained to durable COLD,
- Founder browser opened on Workspace 5 from the same persistent profile,
- the Founder browser command line contained no `--remote-debugging-*` argument,
- automation remained blocked while Founder held the profile,
- closing the Founder window transitioned the hold to CLOSED.

## Cognition robustness discovered during acceptance

Post-cutover observation exposed an existing cognition failure loop unrelated to X11 ownership: `PRODSEED000138` had received a plain-text provider error response instead of JSON. The scheduler repeatedly raised `JSONDecodeError`.

The cognition runtime was hardened so malformed provider responses are now:

1. hash-preserved under `cognition/rejected-responses`,
2. recorded as `E_RESPONSE_MALFORMED`,
3. bounded by the existing semantic-attempt budget,
4. retried with a new request attempt rather than looping forever.

The same acceptance exposed a stale/non-editable ChatGPT composer on the bound Division01 thread. Cognition now performs one bounded page reload and composer reacquisition before failing. Persistent composer failure is classified as bounded `E_COMPOSER_REACQUIRE` transport retry rather than an infinite cron failure.

Because live `/srv/die` intentionally lags canonical source and remains drifted, only the minimal compatibility hotfix was applied to the live cognition runtime. The canonical branch contains the same robustness behavior on the current cognition implementation.

## Scheduler recovery

After recovery:

- direct cognition execution `63fbab8ac4c5414e8d9e4a674b8ab652` completed successfully,
- next automatic builtin execution `90cd912bfc4e4714959c392206933b22` completed successfully,
- both Executive and Division01 were COLD,
- no governed V1 production browser process remained idle,
- `die-principal-browser-broker.service` and `die-muxia-dispatch.service` remained active.

## Security and authority

- no credential values were read,
- no cookies or tokens were copied,
- no CAPTCHA/protection bypass was attempted,
- no public CDP listener was introduced,
- no marketplace submission/publication authority changed,
- no spend authority changed.

Read-only VNC remains optional observation/fallback only; it is not the primary Founder repair/control surface after FA-339.

## Rollback

Live cutover and cognition hardening were backed up under `/var/lib/die/rollback/FA-339/`. Rollback must remain deliberate and must not restore hidden always-on browser ownership from pre-FA-338 services.
