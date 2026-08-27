# MUXIA BROWSER FOUNDATION V1

Status: BATCH MUXIA-B03 COMPLETE
Date: 2026-08-27
Batch: `MUXIA-B03 — Browser Foundation`
Parallel lanes: `MX-P01 Legacy profile metadata probe` + `MX-030 Playwright Chromium driver`

## Outcome

MUXIA now has its first independent browser runtime proof and a sanitized legacy-profile provenance receipt. The new driver does not use Electron, BrowserOS, Proxima browser code, or the legacy Proxima user-data directory.

## MX-P01 — Legacy profile metadata probe

Read-only process metadata identified the active Proxima Electron user-data root as:

`C:\Users\aethers\AppData\Roaming\proxima`

The evidence came from live Electron child-process command lines carrying:

`--user-data-dir=C:\Users\aethers\AppData\Roaming\proxima`

Metadata-only directory inspection showed a `Partitions` root with provider-labelled partitions:

- `chatgpt`
- `claude`
- `deepseek`
- `duck`
- `gemini`
- `grok`
- `mimo`
- `nemotron`
- `perplexity`
- `qwen`

The legacy root also contains names that are credential/session-equivalent or sensitive by nature (`byok.json`, `ipc-token.json`, `Local Storage`, `Network`, `Session Storage`, `Local State`, `Preferences`). Their contents were **not read**.

Binding migration decision:

`DO NOT IMPORT OR COPY THE LEGACY PROXIMA PROFILE ROOT BY DEFAULT`.

MUXIA will instead maintain dedicated profile directories under its own configurable profile root and use operator-controlled authentication/recovery. This avoids cloning a mixed legacy credential/session/runtime boundary.

Machine receipt:

`company/muxia/probes/MX-P01-legacy-profile-metadata.receipt.json`

## MX-030 — Playwright Chromium driver

Runtime dependency added:

- `playwright ^1.62.1`

Playwright-managed browser installed for the Windows proof host:

- Chrome for Testing `151.0.7922.34`
- Playwright Chromium build `v1234`

New source:

- `company/muxia/src/browser/playwright-driver.ts`
- `company/muxia/tests/core/playwright-driver.test.mjs`

### Driver model

MUXIA owns the browser process lifecycle directly:

```text
MUXIA
  -> spawn Chrome for Testing
  -> dedicated --user-data-dir=<profile>/browser
  -> --remote-debugging-address=127.0.0.1
  -> --remote-debugging-port=0
  -> wait for DevToolsActivePort
  -> verify loopback /json/version
  -> Playwright connectOverCDP
```

The debug endpoint is ephemeral and loopback-only by contract. MUXIA records the runtime PID, profile directory, loopback host and ephemeral port for the active handle.

### Lifecycle proven

1. launch dedicated Chromium profile;
2. detect a valid PID;
3. connect Playwright through loopback CDP;
4. open/control a page using a local `data:` URL;
5. stop the browser process;
6. restart against the same persistent profile directory;
7. prove directory identity persists while process/debug identity is disposable;
8. reject a second launch while the driver already owns an active browser;
9. reject profile directories outside the configured profile root.

### Windows hardening discovered during proof

Two defects were found and repaired inside MX-030 before acceptance:

1. **`DevToolsActivePort` transient lock race** — Windows may expose the file before it is readable. The readiness loop now retries `ENOENT`, `EBUSY`, and `EACCES` until the bounded launch deadline.
2. **test teardown ordering** — test cleanup initially attempted to remove a profile directory before Chromium stopped, causing a test-runner hang. Teardown now enforces `stop browser -> delete temp profile`.

Browser shutdown is bounded. MUXIA first requests browser closure over CDP, then performs bounded process wait and process-tree termination if graceful shutdown does not finish. The test harness verified no retained active MUXIA driver after stop.

Targeted MX-030 verification:

`4 passed / 0 failed`.

## Security/policy boundaries

B03 did not:

- open ChatGPT or another provider website;
- submit prompts or extract provider output;
- read/export cookies, tokens, browser localStorage/sessionStorage, or profile databases;
- import Proxima browser state;
- use stealth/fingerprint/protection-bypass flags;
- alter Proxima runtime;
- generate production assets;
- submit/publish/spend.

MX-P03 remains binding: consumer ChatGPT web output acquisition is operator-controlled under the current policy gate.

## Next eligibility

With MX-030 complete, the next chained provider-bound node is:

`MX-031 — ChatGPT provider state detector`.

MX-031 may detect safe visible states (`READY`, auth-required, protection/rate-limit/unknown) but must not implement bypass or automated consumer-web Output extraction.
