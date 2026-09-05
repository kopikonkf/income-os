# Factory ↔ MUXIA Provider Boundary v1

**Task:** FA-113  
**Status:** CANONICAL CANDIDATE  

## Decision

MUXIA remains the sole owner of the ChatGPT browser runtime, authenticated Chromium profile, CDP attachment, session lifecycle, prompt dispatch, completion detection, provider-original acquisition and export from MUXIA private storage. Factory Asset does **not** spawn a second browser, copy credentials, read cookies/tokens, attach separately to the same profile, or dereference `/var/lib/muxia/artifacts`.

Factory begins only after MUXIA has exported verified bytes into the assigned DIE workspace:

```text
Factory job / Blueprint
        |
        v
MUXIA queue request
        |
        v
MUXIA-owned BROWSER_CDP runtime
        |
        +-- private artifact: /var/lib/muxia/artifacts/...   [MUXIA only]
        |
        v
verified export
/var/lib/die/workspaces/<task>/provider/source-original.*
        |
        v
FA-113 compatibility adapter
        |
        +--> Factory GENERATE_RESULT
        +--> provider-original intake receipt
        +--> master-facts
        |
        v
Factory postproduction
```

## Authority boundary

The adapter passes only when upstream MUXIA evidence says prompt submission and output extraction were automated, credential values and cookies/tokens were not read, publication/submission authority remained false, and Hermes did not access the private MUXIA artifact. Any contradiction fails closed.

The adapter itself contains no subprocess/browser/CDP/profile-launch path. It consumes only the exported workspace artifact and the sanitized MUXIA queue receipt.

## Contract mapping

MUXIA current Linux evidence maps to Factory as:

- provider ID: `chatgpt`;
- transport: `BROWSER_CDP`;
- image generation: true;
- currently evidenced output format: PNG;
- capacity: `UNKNOWN`;
- operator actions after dispatch: zero when automation flags are true;
- provider original: exact exported bytes, re-hashed and strictly decoded by Factory intake;
- canonical master state: **not** written by the adapter; intake remains `STAGED_NOT_CANONICAL` and still requires the State Manager boundary.

## Relationship to `kopikonkf/web-ai-adapter`

The Windows `web-ai-adapter` work is the provider-behavior proving ground and source of transport-specific knowledge. It demonstrated that ChatGPT, Gemini, Manus and Duck.ai can satisfy the zero-touch BROWSER_CDP contract, while Qwen can use SESSION_API primary plus BROWSER_CDP fallback. That evidence is reusable.

What is **not** reused on Linux is a second browser/session owner. For ChatGPT, MUXIA already provides the live Linux browser substrate, so FA-113 normalizes its result into the Factory contract instead of transplanting the standalone Windows browser lifecycle. Later provider extraction tasks should reuse the minimum provider-specific logic necessary while attaching to the governed shared runtime or using a cleaner non-browser transport where canon explicitly permits it.

This preserves standalone ↔ MUXIA rollback/coexistence as historical operational resilience without turning coexistence into simultaneous ownership of one production session.
