# H01 NexaBurst P001 acceptance - 2026-09-19

- Dedicated Brave UDD: nexaburst-p001
- Display: :12 / Workspace 4
- CDP: loopback 127.0.0.1:9311
- Web session auth persisted across dedicated Brave restart
- Unlimited entitlement remained active after restart
- direct Web job API acquisition proven
- 20/20 final soak artifacts produced
- one transient provider terminal failure observed: image URL absent in upstream response; retry succeeded
- no HTTP 429 observed in soak
- post-restart generation canary PASS: 1024x1024, 15.157s
- actual Nexa raw -> Factory V2 -> WAITING_FOUNDER_QC PASS
- >100 batch production interlock tested fail-closed
- raw and V2 disk admission gates enabled
