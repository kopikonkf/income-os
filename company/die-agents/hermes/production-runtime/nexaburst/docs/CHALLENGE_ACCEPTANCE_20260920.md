# H01 NexaBurst 30-Render Visual Challenge Acceptance — 2026-09-20 WIB

## Design
10 anchor nouns × 3 deterministic typed presets = 30 provider-original renders.

Anchors:
bottle, chair, hammer, laptop, gift box, backpack, frying pan, umbrella, potted plant, trophy.

Presets:
1. ISOLATED_SOFT_WATERCOLOR_CLIPART_WHITE_L0
2. ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0
3. ISOLATED_CLEAN_COMMERCIAL_CLAY_3D_L0

All prompts:
- prompt_authority = TYPED_VISUAL_CONTRACT_V1
- deterministic Subject Spec + Preset + Visual Requirement Spec + canonical Prompt Compiler
- no LLM in challenge hot path

Typed queue:
- path: config/challenge-30-typed.jsonl
- rows: 30
- SHA256: cde89c197fc3cce015396b9ca246ae795fb9064aef587d0ccfca10611bc228a6

## Generation result
- 30/30 final artifacts DONE
- failed final artifacts: 0
- HTTP 429: 0 observed
- overall median: 13.0295s
- overall mean: 18.1916s
- one watercolor-backpack outlier: 136.520s
- backend progress for outlier included server-busy retry and recovered without client duplicate submission

Per preset:
- Soft Watercolor Clipart: 10/10, median 14.043s, mean 26.4173s
- Premium Semi-Realistic Digital: 10/10, median 14.881s, mean 14.2053s
- Clean Commercial Clay 3D: 10/10, median 12.947s, mean 13.9522s

## Deterministic visual hygiene
Soft Watercolor:
- border white 99.96%
- average foreground 21.14%
- average minimum margin 8.49%
- clipped 0/10

Premium Semi-Realistic:
- border white 99.98%
- average foreground 24.36%
- average minimum margin 7.90%
- clipped 0/10

Clean Clay 3D:
- border white 99.99%
- average foreground 23.46%
- average minimum margin 7.67%
- clipped 0/10

## Founder visual-review surface
Three contact sheets:
- /var/lib/die/h01/nexaburst/challenge/challenge-30-20260920/wc-contact-sheet.jpg
- /var/lib/die/h01/nexaburst/challenge/challenge-30-20260920/sr-contact-sheet.jpg
- /var/lib/die/h01/nexaburst/challenge/challenge-30-20260920/clay-contact-sheet.jpg

Telegram NexaBurst reporting topic:
- chat_id: -1004358461724
- message_thread_id: 5834
- challenge report summary message_id: 5852
- technical completion message_id: 5853

## V2 / Vault boundary
All 30 challenge IDs are in:
- /var/lib/die/h01/nexaburst/state/v2-hold-ids.txt

They MUST NOT be postprocessed merely because the provider render exists. The 30-render challenge is a preset-selection experiment.

Telegram Vault remains a separate downstream layer and only archives artifacts that actually reach WAITING_FOUNDER_QC.

## Prepared market canary
100-noun candidate cohort:
- path: config/market-canary-100-source.jsonl
- rows: 100
- SHA256: 93ed16a3ebc7eed8934d8c26f43658faf5820dd81d433d4d8afeadd0028a5054
- state: HOLD_PENDING_FOUNDER_VISUAL_QC

Release requires:
1. FOUNDER_PRESET_CHAMPION
2. TYPED_VISUAL_CONTRACT_V1_COMPILED_FOR_100
3. DISK_GATE_PASS

No 100-noun production has been dispatched.
