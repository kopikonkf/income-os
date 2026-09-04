# Rights / Brand / Watermark Signal Gate v1

Task: `FA-136`
Status: PASS
Date: 2026-09-04

This component is an automated **signal gate**, not a legal-clearance engine. Every evaluation is bound to the exact master SHA-256.

Routes:
- `PASS`: required detector evidence is complete and no observable automated blocker/review signal is present;
- `REVIEW_REQUIRED`: detector evidence is incomplete/uncertain, visible text remains unresolved, or logo/watermark/trademark/safety candidates need human review;
- `BLOCK`: confirmed stock watermark, confirmed trademark term, confirmed brand logo or blocking safety signal.

A `PASS` does not grant human rights/IP clearance, submission authority or publication authority. `human_rights_clearance=false` and `founder_qc_required=true` are invariant. Unknown detector state never becomes PASS.

The current gate consumes detector observations; future OCR/logo models may feed the same contract without changing Hermes/postproduction policy.