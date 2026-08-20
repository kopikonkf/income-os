# SCOREBOARD.md — Organism Test Phase A (B3.3)

| Metrik | Target | D1 | D2 | D3 | D4 | D5 | D6 | D7 | **LULUS/GAGAL** |
|--------|--------|----|----|----|----|----|----|----|----------------|
| **projection_accuracy** | ≥ 0.75 (3/4) | - | - | - | - | - | - | - | GAGAL |
| **truth_vs_projection_drift** | 0 | - | - | - | - | - | - | - | GAGAL |
| **raw_access_violations** | 0 | - | - | - | - | - | - | - | GAGAL |
| **wake_accuracy** | 1.0 (budget respected) | - | - | - | - | - | - | - | GAGAL |
| **briefing_completeness** | complete | - | - | - | - | - | - | - | GAGAL |
| **fault_detection** | detected ≤ 15 min | - | - | - | - | - | - | - | GAGAL |
| **proposal_quality** | ≥ 1 valid proposal | - | - | - | - | - | - | - | GAGAL |

## Ringkasan 7 Hari
- **Total LULUS**: 0/7
- **Total GAGAL**: 7/7
- **Keputusan Gerbang**: BLOKIR (belum memenuhi syarat keluar Phase A)

## Catatan per Hari
- **D1**: Baseline — conformance run, ground-truth sampling
- **D2**: Gateway down 20 menit — system_health latency, event CRITICAL, wake
- **D3**: ChatGPT #A proposal — proposal format, Hermes response time
- **D4**: Test fail + done tanpa evidence — gate rejection, card blocked, WARNING
- **D5**: 6 forbidden requests — E_NO_RAW_ACCESS, ACCESS.jsonl rejected
- **D6**: Bridge down 1 siklus — briefing absence detection, seq monotonic
- **D7**: Full conformance re-run — aggregate scoring, phase gate decision