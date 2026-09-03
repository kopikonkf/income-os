# Factory Asset OAUTH Security Remediation Plan v1

**Task:** FA-004
**Date:** 2026-09-03
**Scope:** `D:\OAUTH` Git authentication hygiene only
**Execution mode:** PLAN ONLY
**Credential rotation performed:** NO
**Git remote changed:** NO
**Provider/runtime mutation:** NONE

## 1. Objective

Remove inline authentication material from the local `D:\OAUTH` Git remote, rotate the affected credential, preserve repository access through a non-inline credential mechanism, and verify that no credential value remains exposed in current worktree output or repository history.

This task is planning only. Execution is reserved for `FA-005` and requires Founder/operator authority.

## 2. Current evidenced standing

The following facts were verified without reading or publishing the secret value:

- `D:\OAUTH` is repository `kopikonkf/web-ai-adapter` at observed HEAD `bc155d4279b9a5eefe98113ed64ca32e221a59dc`.
- Its current `origin` HTTPS URL contains inline authentication material.
- The remote host/path is GitHub and targets `kopikonkf/web-ai-adapter`.
- Git for Windows has `credential.helper=manager` configured from the system Git config.
- GitHub CLI is already authenticated to GitHub as the active account through the OS keyring and uses HTTPS Git operations.
- `credentials/` is ignored by the repository, and raw session/capture material is intentionally excluded from normal source control.
- The OAUTH tree is dirty and must not be reset, cleaned, stashed, or otherwise repurposed during remediation.

No credential value was opened, logged, copied, or committed while establishing these facts.

## 3. Target authentication state

After FA-005, the repository remote must have the canonical shape:

```text
https://github.com/kopikonkf/web-ai-adapter.git
```

Authentication must be supplied out-of-band by the existing OS-backed Git credential mechanism, preferably the already-installed Git Credential Manager / GitHub CLI keyring integration.

Forbidden target states:

- token/PAT embedded in remote URL;
- token in `.git/config` plaintext;
- token in repository files, `.env`, scripts, shell history, logs, receipts, or documentation;
- copying the affected token into another credential store without rotation;
- moving provider session cookies into Git authentication configuration.

## 4. FA-005 execution sequence

FA-005 should execute in the following order and stop immediately if any validation fails.

### Step A — Preserve pre-change evidence

Record only sanitized facts:

- exact repository HEAD;
- dirty-path count and status digest, not sensitive file contents;
- sanitized remote host/path;
- credential-helper mechanism;
- active GitHub account identity;
- timestamp.

Do not stage, stash, reset, clean, checkout over, or rewrite the dirty OAUTH worktree.

### Step B — Establish replacement Git authentication

Use the existing non-inline mechanism already available on the host:

1. verify GitHub CLI/keyring authentication is active;
2. verify Git Credential Manager is configured;
3. ensure the authenticated principal has repository access;
4. do not expose token values in command output.

A read-only remote probe should be performed before removing the inline remote only if it can be done without printing credentials.

### Step C — Remove inline authentication from `origin`

Replace the local remote URL with:

```text
https://github.com/kopikonkf/web-ai-adapter.git
```

Immediately verify:

- `git remote get-url origin` contains no userinfo component;
- `git ls-remote origin HEAD` succeeds through the non-inline credential mechanism;
- repository HEAD/worktree contents remain unchanged.

Failure to access the repository after sanitization must stop the task. Do not restore an inline credential as an automatic fallback.

### Step D — Rotate/revoke the affected credential

The credential embedded in the old remote must be treated as exposed and rotated/revoked through its issuing authority.

Because credential issuance/revocation is an account-security action, this step requires Founder/operator authority and may require interactive GitHub UI/CLI handling.

Requirements:

- identify the affected credential by account-side metadata, never by publishing its value;
- revoke/rotate it;
- verify repository access still succeeds with the non-inline mechanism;
- do not copy the old value into any replacement location.

If the exact credential cannot be safely identified without revealing secret material, stop with `WAITING_OPERATOR` rather than guessing.

## 5. Secret exposure scan plan

FA-005 must scan both the current tree and reachable Git history for evidence that an inline credential or equivalent secret was committed or emitted.

### Current worktree / tracked files

Scan tracked text files for secret-shaped patterns, including:

- GitHub PAT prefixes / token-like strings;
- `Authorization: Bearer ...` with literal values;
- remote URLs containing `https://userinfo@github.com/...`;
- plaintext `token=`, `password=`, `api_key=` or equivalent assignments where values are not placeholders.

Do not print matching secret values. Scanner output must report only:

- path;
- line number where safe;
- secret class;
- redacted fingerprint/digest.

Untracked raw HAR/session/capture files remain local evidence. They should be scanned only with a redaction-safe scanner if required; their contents must not be copied into receipts.

### Git history

Search reachable commits for:

- historical `.git` remote URLs cannot be committed directly, but scripts/docs may contain copied authenticated URLs;
- GitHub token-like patterns;
- hard-coded authorization headers;
- credential JSON or `.env` files accidentally committed.

If a real secret is found in Git history, FA-005 must not silently rewrite repository history. It should stop and create a separate Founder-authorized history-remediation task because history rewrite is disruptive and requires coordination.

## 6. Shell/log hygiene

FA-005 must avoid commands that echo the old remote verbatim after identifying that it contains inline auth.

Rules:

- sanitize remote URLs before logging;
- do not run verbose Git HTTP tracing with credentials enabled;
- do not export tokens into process command lines;
- do not persist credentials in PowerShell history;
- receipts contain hashes/fingerprints only, never secret values;
- delete only task-created temporary sanitized scan files after use; do not delete existing OAUTH evidence files.

## 7. Verification contract

FA-005 passes only if all conditions are true:

1. `origin` contains no inline authentication/userinfo.
2. Git fetch/ls-remote access succeeds using the non-inline credential mechanism.
3. The affected inline credential is rotated/revoked.
4. OAUTH repository HEAD is unchanged except for intentionally local `.git/config` remote metadata.
5. Dirty source/worktree files are unchanged.
6. Current tracked-file secret scan is clean, or findings are separately dispositioned without leaking values.
7. Reachable-history scan is clean, or a separate Founder-authorized history remediation is opened.
8. No credential/session value appears in receipts, console transcript, committed docs, or Git diff.
9. Provider text/image runtime behavior is untouched by the security remediation.

## 8. Rollback and failure behavior

There is no rollback to the old inline credential.

If repository access fails after sanitizing the remote:

```text
STOP
  -> keep sanitized remote
  -> repair OS-backed Git authentication interactively
  -> verify access
  -> continue only when green
```

Never restore the exposed credential into the URL as a convenience rollback.

If credential rotation occurs before replacement access is verified, stop and repair authentication through Git Credential Manager / GitHub CLI rather than embedding a new secret.

## 9. Separation from provider credentials

This remediation concerns Git repository authentication only.

It must not:

- rotate Qwen/Gemini/ChatGPT/Grok/Manus/Duck.ai browser or session credentials;
- copy provider cookies between principals;
- alter `credentials/*.json`;
- log into providers;
- start image generation;
- change OAUTH provider code.

Those concerns remain under FA-W000 onward.

## 10. Receipt requirements for FA-005

The FA-005 receipt should contain only sanitized evidence:

```text
repository
head_before
head_after
remote_before_inline_auth = true|false
remote_after_inline_auth = false
remote_after_host_path
credential_helper
replacement_access_probe = PASS|FAIL
affected_credential_rotation = PASS|WAITING_OPERATOR
tracked_secret_scan = PASS|FINDINGS
history_secret_scan = PASS|FINDINGS
dirty_tree_digest_before
dirty_tree_digest_after
provider_runtime_mutation = false
secret_value_logged = false
```

No token, cookie, authorization header, raw credential file, or authenticated capture may be attached.

## 11. FA-004 acceptance verdict

**PASS — PLAN COMPLETE.**

The remediation plan removes inline Git authentication, rotates the affected credential, preserves repository access through OS-backed authentication, scans current/tree history safely, preserves the dirty OAUTH worktree, and prevents secret values from entering logs or receipts.

Actual mutation remains blocked behind `FA-005 — Execute Founder-authorized OAUTH credential remediation`.
