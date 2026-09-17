# FA-338 — Demand-Driven V1 Browser Ownership

Status: **DONE / PASS**  
Date: 2026-09-17

FA-338 implements the FA-337 contract without merging Factory Asset V1 and V2. V1 persistent browser profiles remain durable on disk, while browser processes become job-scoped.

## Production runtime

V1 Runtime 01/02 no longer require always-on external Chrome owners or always-on cluster brokers. The production path is now:

```text
COLD
  -> scheduler admission
  -> spawn job-scoped Xvfb + headful Chrome
  -> start job-scoped MUXIA broker
  -> live provider readiness
  -> exactly-once provider dispatch
  -> durable terminal or committed-unresolved receipt
  -> Browser.close / bounded process cleanup
  -> prove CDP closed + broker control closed + profile process gone + lease released
  -> COLD
```

The lightweight dispatch/control plane may remain resident, but queue-empty state owns no governed production browser renderer or CDP listener.

## Cognition ownership boundary

`die-hermes` does not own Executive or Division01 browser processes and does not need write access to their persistent profiles.

A local Unix-socket broker runs as `kopiko:die-runtime`:

```text
die-hermes cognition tick
  -> /run/die/principal-browser-broker.sock
  -> principal browser broker (kopiko)
  -> job-scoped Xvfb + headful Chrome from persistent principal profile
  -> loopback CDP readiness
  -> cognition roundtrip
  -> durable cognition receipt
  -> STOP request with terminal evidence
  -> browser/Xvfb close
  -> COLD
```

The broker has no public TCP listener. The Unix socket is `0660 kopiko:die-runtime`. CDP remains loopback-only. Browser ownership is bounded to one admitted cognition job.

## Auth and protection challenges

If live readiness returns `AUTH_REQUIRED` or `CHECKPOINT`, automation fails closed. A durable auth-repair hold blocks that profile from further automated admission. Founder repair uses the same persistent profile headfully with CDP disabled. The system does not automate CAPTCHA/protection bypass and does not read or copy credential/session bytes.

## Live acceptance

`PRODSEED000133` proved the complete chain:

- Division01 author R01 completed through the Unix-socket broker and returned COLD.
- Executive reviewer R00 returned `NO_VETO` and returned COLD.
- Cognition state became `READY`; production resumed automatically.
- V1 Runtime 02 spawned on demand, selected Manus, committed once, acquired the provider original, wrote a successful dispatch receipt, and returned COLD.
- Browser process, CDP endpoint, broker control endpoint and runtime lease were all released.
- Cognition cron recovered from the previous failure streak; both a direct scheduler run and the next builtin minute run completed successfully.

A separate postproduction format-support gap was exposed after successful FA-338 browser lifecycle acceptance: the Manus provider-original was WebP and the current upscale stage rejected it with `E_UNSUPPORTED_RASTER`. That is not a browser-ownership failure and is not part of FA-338.

## Rollback

Historical external browser-owner/broker units remain present as explicit rollback material but are disabled in the FA-338 operating model. Re-enabling them requires deliberate rollback action; historical installers are gated to prevent silently restoring always-on ownership.
