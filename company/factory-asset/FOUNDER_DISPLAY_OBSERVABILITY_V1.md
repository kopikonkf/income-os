# Founder-visible Production Display Observability v1

Task: `FA-323`

Founder observation must target the **actual production browser displays** (`cluster-a :101`, `cluster-b :102`) rather than the unrelated XFCE/xrdp desktop. Default observation is read-only. Browser CDP and broker controls remain loopback-only and are never exposed as Founder-facing public endpoints.

FA-323 defines only the contract. FA-324 may attach local-only read-only VNC mirrors to these exact displays through SSH local forwarding. FA-325 separately governs temporary interactive auth/recovery with an exclusive repair lease and explicit revocation. Observation never permits reading or exporting passwords, cookies, tokens, browser storage, or raw credential material.
