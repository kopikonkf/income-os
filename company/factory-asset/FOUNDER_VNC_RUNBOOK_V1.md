# Founder VNC Runbook v1

Status: FA-324/FA-325 accepted implementation.

Production browser displays are observed through loopback-only VNC endpoints on the Linux VPS. Cluster A uses `127.0.0.1:59101` for read-only observation of Xvfb `:101`; Cluster B uses `127.0.0.1:59102` for Xvfb `:102`. These services join the browser-owner PrivateTmp namespace, so they observe the real production browser without restarting or cloning the browser profile.

Founder access must use SSH local forwarding; no VNC, CDP or broker port may be exposed publicly. Example from a trusted workstation: `ssh -L 59101:127.0.0.1:59101 -L 59102:127.0.0.1:59102 -p 25013 kopiko@<linux-host>`. A local VNC viewer then connects to `127.0.0.1:59101` or `127.0.0.1:59102`.

Temporary interactive repair is separate from observation. `founder_browser_repair.py open --cluster cluster-a --timeout 900` (or cluster-b) requires an idle broker with zero active tab leases, creates a time-bound repair hold, stops the read-only observer for that cluster, starts loopback-only interactive VNC on `59201` (A) or `59202` (B), and restores read-only observation after timeout. The production dispatcher skips a cluster while its repair hold is ACTIVE.

`revoke --cluster <cluster>` closes the interactive service and restores read-only observation. Interactive services are not enabled at boot. The workflow never reads/copies credentials, cookies or tokens and does not bypass CAPTCHA or provider security checkpoints.

Rollback for observability only: disable/stop `die-founder-vnc-cluster-a.service` and `die-founder-vnc-cluster-b.service`. Do not stop or restart `die-muxia-cluster-*-browser.service` for VNC rollback.
