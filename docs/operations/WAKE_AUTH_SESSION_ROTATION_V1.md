# Wake Auth/Session Rotation and Revocation v1

Date: 2026-08-23
Owner: Founder / delegated local VPS operator
Architect role: versioned controls and read-only verification

## Safety boundary

This runbook describes controlled recovery. It does not authorize the Architect
or Hermes to inspect tokens, dump cookies, delete a profile, sign out an
account, restart an unrelated browser, change a scheduled task, or rotate a
credential without Founder/delegated-operator authority.

Never record a credential value while following this runbook.

## Never record

- Web JWT, Codex access token, refresh token, ID token;
- browser cookies or local/session storage;
- Authorization or sentinel headers;
- sentinel requirement token, PoW seed/config/proof;
- raw `/api/auth/session` or backend error body;
- browser/CDP message dump;
- `auth.json` contents.

Allowed receipt fields are principal/division ID, timestamp, event ID, outcome,
sanitized error code, latency, thread generation, and evidence reference.

## Normal expiry

Trigger: wake returns a sanitized 401/403 or reports no active web session.

1. Stop retries after the first classified failure.
2. Record `auth_stale` with principal, error code, and timestamp only.
3. Verify the expected CDP endpoint is loopback-only and mapped to the expected
   principal; do not inspect cookies or token values.
4. Founder/delegated operator opens the dedicated browser profile and completes
   normal ChatGPT sign-in/MFA.
5. Run a read-only wake health/list probe.
6. Send one bounded canary wake only after the probe passes.
7. Resolve the alarm with the evidence reference. Do not paste the response or
   session object into the event.

Web-session recovery does not require creating or refreshing Codex OAuth
credentials.

## Rotation

### Canonical thread rotation

Use when the active thread is too large, corrupted, or intentionally replaced.

1. Capture the current thread generation and canonical state references.
2. Send a compact handoff that contains no credentials and no raw signed
   payloads.
3. Invoke `--new` once.
4. Verify the new `wake.json` generation is active and the previous thread is
   marked `superseded` with `superseded_by` set.
5. Emit a metadata-only rotation receipt.
6. Verify the next wake routes to the new thread.

At no time may two thread mappings be marked active for one division/principal.

### Codex OAuth cache rotation

The Codex cache is not used by wake. If a real Codex consumer requires it:

1. Prefer the OS credential store/keyring supported by Codex.
2. For file fallback, verify `auth.json` and its parent are outside the repo and
   readable only by the intended user plus explicitly approved OS recovery
   principals. Inspect ACL metadata, never file contents.
3. Use the supported Codex login/logout flow for rotation. Do not hand-edit or
   print token fields.
4. If no Codex consumer requires this cache, Founder may revoke/remove it as a
   separate destructive credential action.

## Suspected compromise

Treat any unexpected CDP exposure, unknown target control, token/header in a
log, copied browser profile, or cross-principal response as compromise.

1. Pause wake for the affected principal; do not attempt repeated probes.
2. Record a CRITICAL sanitized incident and notify Founder.
3. Under explicit authority, isolate the affected browser/CDP process from the
   network and stop its wake schedule.
4. End the ChatGPT web session using the provider-supported logout/security
   controls and clear the affected dedicated browser data as authorized.
5. Revoke/clear any separate Codex cache with the supported Codex logout flow if
   that credential domain may also be affected.
6. Review repository, event, receipt, session, and application logs for secret
   values without copying them into evidence. Redact and rotate affected logs.
7. Recreate the browser credential domain, sign in with MFA, and rebind exactly
   one canonical thread.
8. Run health, principal-binding, and one bounded canary proof.
9. Founder closes the incident only after zero cross-principal access and zero
   residual credential exposure are verified.

## Revocation

Planned revocation of a division/account follows this order:

1. mark the canonical thread archived/superseded;
2. disable the wake schedule/skill for that principal under authorized change;
3. end the browser web session;
4. revoke/remove the Codex OAuth cache separately if it exists;
5. remove the dedicated browser user-data directory only with destructive-action
   approval;
6. retain metadata-only evidence and canonical business state;
7. verify the retired CDP port has no listener and no wake route remains.

## Post-recovery PASS

```text
CDP local address = 127.0.0.1 or ::1
principal binding = expected principal
division binding = expected division or null for Executive
web JWT exported from page = false
auth/session secret in logs/events/artifacts = 0
active canonical threads per principal/division = 1
health/list probe = pass
bounded canary wake = pass
incident/alarm receipt = metadata only
```
