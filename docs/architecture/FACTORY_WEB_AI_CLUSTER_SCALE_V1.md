# Factory Web-AI Cluster Scale and Unified Control Plane v1

## Decision

`/var/lib/muxia/profiles/chatgpt-linux-a/browser` is accepted as historical evidence and the first **Web-AI Army Cluster A** persistent profile. The name is not migrated merely for aesthetics. A cluster may persist authenticated sessions for multiple provider domains.

The central active-tab ceiling is **8**. This is a capacity ceiling inside one Chromium process, not permission for multiple Chromium processes to open the same `user-data-dir`.

## Concurrency invariant

```text
ONE CLUSTER PROFILE
      |
      v
ONE CHROMIUM OWNER PROCESS (MUXIA broker)
      | loopback CDP
      +-- tab lease: ChatGPT
      +-- tab lease: Qwen
      +-- tab lease: Gemini
      +-- tab lease: Manus
      +-- tab lease: Duck.ai
      +-- spare/recovery tabs up to total ceiling 8
```

Until FA-301/FA-302 are complete, raising the ceiling to 8 does **not** by itself prove simultaneous five-provider production. Existing runners that independently launch Chromium against the same persistent profile must remain serialized.

## Cluster membership model

Cluster A currently has evidenced or active candidates: ChatGPT, Qwen, Gemini, Manus and Duck.ai. Grok is separately deferred/policy-capacity gated and never blocks a healthy five-provider pool. Session state is domain-scoped inside the shared persistent profile; credential, cookie and OAuth-token values are never exported into Factory receipts.

## Qwen transport

Factory keeps Qwen `SESSION_API` as the preferred transport in its clean adapter because it is lighter when an opaque session can be acquired and governed safely. The accepted Linux FA-112 live canary used `BROWSER_CDP` fallback through Cluster A because Linux had no approved opaque SESSION_API auth handoff. Production routing must report the actual transport used per attempt rather than pretending all Qwen jobs use SESSION_API.

## Multi-cluster scale

A cluster is a bounded capacity unit, not an unlimited worker. Scaling toward 1K-5K unique masters/day is achieved by measured replication of clusters plus provider-aware routing, queue backpressure, circuit breakers, QA/postproduction capacity and economics. Profiles are provisioned independently; session secrets are not copied from Cluster A to B/C/D.

## Unified control plane

Factory Console v2 should remain **web-first**. Recommended implementation boundary:

- UI: TypeScript + React + lightweight utility CSS; dark dense operations layout.
- Control API / canonical Factory state: keep existing Python Factory core/state-manager boundary; expose typed HTTP APIs rather than duplicating logic in UI.
- MUXIA browser/cluster runtime: Node.js/TypeScript, because current CDP/browser runtime is already proven there.
- Live events: SSE initially; WebSocket only where bidirectional high-frequency control materially requires it.
- Storage: canonical Factory state remains authoritative; UI cache/index must never become a second SSOT.
- Desktop: optional Tauri thin shell after the web control plane is stable. Rust is packaging/native integration, not a rewrite requirement. Electron is not the default because the project already moved away from a heavier Electron browser mental model.

The uploaded 9router interface is used only as a clean-room interaction reference: persistent left rail, categorized provider cards, compact connection/status pills, usage/quota visibility and global actions. Factory substitutes domain concepts: Blueprint, Production Queue, Clusters, Providers, Assets, QA/QC, Marketplace, Usage/Economics, Logs and Settings. No 9router source/assets are copied.

## DIE federation boundary

Factory Console is a domain control plane. A future DIE holding-company dashboard can federate it later through stable event/command/deep-link contracts. Factory should therefore be a module that can be embedded or linked, not a UI that owns company-wide truth.
