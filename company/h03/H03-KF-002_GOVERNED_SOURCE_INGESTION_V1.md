# H03-KF-002 - Governed External Source Ingestion v1

Status: DONE / PASS
Date: 2026-09-09

External acquisition and knowledge acceptance are separate operations. An HTTP client, browser, connector, crawler or web tool may acquire bytes, but acquisition never implies truth or rights acceptance.

```text
external bytes
-> immutable source identity + raw SHA-256
-> deterministic normalization
-> evidence-unit SHA-256
-> PENDING_REVIEW
-> permitted reviewer authority
-> accepted external source packet
-> later claims/Knowledge Package
```

Accepted reviewer kinds are `FOUNDER`, `ARCHITECT`, and `GOVERNED_RULESET`. `LLM`, `CRAWLER`, `PROVIDER_MODEL`, and `WEB_AI` are mechanically rejected as review authorities. Rights state `UNKNOWN` also fails closed.

The adapter does not fetch credentials, browser profiles, cookies or provider sessions, and it does not write canonical Company Truth. `canonical_truth=false` remains explicit in both snapshot and accepted source packet.

Supported deterministic normalization in v1: UTF-8 plain text and HTML visible-text extraction. Raw external bodies need not be committed to Git; hashes and governed source identity allow durable lineage while retention policy remains separate.
