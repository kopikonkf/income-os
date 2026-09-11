import tempfile
import unittest
from pathlib import Path

from company.h03.lib import artifact_courier
from company.h03.lib import live_org_runner as mod


class FakeClient:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)
        return {"ok": True}


class FakeWorker:
    def __init__(self, courier):
        self.courier = courier
        self.calls = []

    def _resolve_inputs(self, card):
        out = []
        for ref in card.get("input_artifacts") or []:
            if str(ref.get("ref", "")).startswith("artifact://h03/"):
                out.append(self.courier.resolve(ref))
        return out

    def run(self, *, run_id, card, instruction, max_routes=3, timeout_seconds=180,
            dominant_producer_provider=None, preferred_provider=None, payload_validator=None):
        self.calls.append(card["work_card_id"])
        wc = card["work_card_id"]
        inputs = self._resolve_inputs(card)

        if wc.endswith("A-CURATE"):
            candidates = []
            for i in range(8):
                candidates.append({
                    "problem_seed_id": f"H03-PS-LIVE-{i+1:03d}",
                    "persona": {
                        "actor": "remote professionals",
                        "qualifier": f"who repeatedly handle admin workflow {i+1}",
                    },
                    "context": "managing recurring digital administrative work across multiple tools",
                    "trigger": "a repeated weekly coordination task becomes error-prone and time consuming",
                    "job_to_be_done": "complete the recurring administrative workflow reliably with less rework",
                    "pain": {"statement": "repeated manual tracking causes missed steps, duplicated work, and uncertainty"},
                    "desired_outcome": "use a repeatable structured workflow that reduces missed steps and rework",
                })
            payload = {"candidates": candidates}

        elif wc.endswith("B-MARKET-SCOUT"):
            seeds = inputs[0]["candidates"][:2]
            payload = {"candidate_sources": []}
            for idx, seed in enumerate(seeds, 1):
                payload["candidate_sources"].append({
                    "problem_seed_id": seed["problem_seed_id"],
                    "source_requests": [
                        {"url": f"https://example.com/{idx}/paid", "source_class": "COMPETITOR_PRODUCT", "signal_hint": "PAID_SUBSTITUTE", "relevance_terms": ["pricing", "workflow"]},
                        {"url": f"https://example.com/{idx}/pain", "source_class": "SPECIALIST_PUBLICATION", "signal_hint": "REPEATED_PAIN", "relevance_terms": ["manual", "rework"]},
                        {"url": f"https://example.com/{idx}/intent", "source_class": "SEARCH_DEMAND", "signal_hint": "PURCHASE_INTENT_SEARCH", "relevance_terms": ["template", "checklist"]},
                    ],
                })

        elif wc.endswith("B2R1-MARKET-RECOVERY"):
            seeds = inputs[0]["candidates"][:2]
            payload = {"candidate_sources": []}
            for idx, seed in enumerate(seeds, 1):
                payload["candidate_sources"].append({
                    "problem_seed_id": seed["problem_seed_id"],
                    "source_requests": [
                        {"url": f"https://recovery.example/{idx}/pricing", "source_class": "COMPETITOR_PRODUCT", "signal_hint": "PAID_SUBSTITUTE", "relevance_terms": ["pricing", "plans", "workflow"]},
                        {"url": f"https://authority.example/{idx}/pain", "source_class": "SPECIALIST_PUBLICATION", "signal_hint": "REPEATED_PAIN", "relevance_terms": ["manual", "rework", "workflow"]},
                    ],
                })

        elif wc.endswith("C-R1-MARKET-EVAL"):
            seed_batch, bundle, eligibility = inputs[0], inputs[1], inputs[2]
            pid = eligibility["eligible_candidates"][0]["problem_seed_id"]
            candidate_sources = [s for s in bundle["verified_sources"] if s.get("candidate_id") == pid]
            source_ids = [s["source_id"] for s in candidate_sources]
            paid_id = next(s["source_id"] for s in candidate_sources if s.get("signal_hint") == "PAID_SUBSTITUTE")
            pain_id = next(s["source_id"] for s in candidate_sources if s["source_id"] != paid_id)
            payload = {
                "selected_problem_seed_id": pid,
                "pain_observation": {"severity": "MEDIUM", "frequency": "HIGH", "urgency": "MEDIUM"},
                "buyer_intent_state": "MEDIUM",
                "productability_state": "HIGH",
                "productability_source_ids": [pain_id],
                "evidence": [
                    {"evidence_id": "MKT-E1", "signal_type": "PAID_SUBSTITUTE", "source_ids": [paid_id], "rationale": "A paid structured substitute exists."},
                    {"evidence_id": "MKT-E2", "signal_type": "REPEATED_PAIN", "source_ids": [pain_id], "rationale": "The workflow pain is repeated and operationally costly."},
                ],
                "selection_reasons": [
                    "Recurring operational friction is documented.",
                    "A paid substitute supports medium willingness-to-pay evidence.",
                ],
            }

        elif "-SCOUT" in wc and "LIVE001-D" in wc:
            plan = next(x for x in inputs if isinstance(x, dict) and x.get("schema_version") == "die.h03.research-plan.v1")
            idx = int(wc.split("LIVE001-D", 1)[1].split("-", 1)[0])
            q = plan["questions"][idx - 1]
            classes = q["required_source_classes"][:2]
            payload = {"source_requests": [
                {"url": f"https://example.com/research/{idx}/1", "source_class": classes[0], "relevance_terms": ["workflow", "problem"]},
                {"url": f"https://example.com/research/{idx}/2", "source_class": classes[-1], "relevance_terms": ["solution", "mistake"]},
            ]}

        elif "-ANALYZE" in wc:
            bundle = next(x for x in inputs if isinstance(x, dict) and x.get("schema_version") == "die.h03.live-verified-source-bundle.v1")
            source_ids = [s["source_id"] for s in bundle["verified_sources"]]
            payload = {"findings": [
                {"finding_id": f"{wc}-F1", "text": "Verified source material supports using a bounded repeatable checklist to reduce omitted steps in the recurring workflow.", "source_ids": [source_ids[0]]},
                {"finding_id": f"{wc}-F2", "text": "Verified source material supports reviewing the workflow after completion so recurring mistakes can be identified and corrected.", "source_ids": [source_ids[1]]},
            ]}

        elif wc.endswith("G-SYNTH"):
            evidence = []
            for packet in inputs:
                for src in packet["source_snapshots"]:
                    evidence.extend([u["evidence_id"] for u in src["evidence_units"]])
            evidence = list(dict.fromkeys(evidence))
            payload = {
                "supported_findings": [
                    {"finding_id": "SF1", "text": "A repeatable checklist can reduce omitted workflow steps.", "evidence_refs": [evidence[0]]},
                    {"finding_id": "SF2", "text": "A post-run review can surface recurring mistakes for correction.", "evidence_refs": [evidence[1]]},
                    {"finding_id": "SF3", "text": "Existing structured substitutes indicate buyers already pay to reduce this recurring friction.", "evidence_refs": [evidence[2]]},
                ],
                "contradictions": [],
                "gaps": [],
                "market_wtp_findings": [
                    {"finding_id": "MW1", "text": "The category includes paid structured substitutes.", "evidence_refs": [evidence[2]], "signal_type": "PAID_SUBSTITUTE"}
                ],
                "claims": [
                    {"claim_id": "C1", "text": "Start by listing the recurring workflow steps in the order they must be completed.", "evidence_refs": [evidence[0]]},
                    {"claim_id": "C2", "text": "Use a completion checklist during each run so omitted steps are visible before the workflow is closed.", "evidence_refs": [evidence[0]]},
                    {"claim_id": "C3", "text": "After each run, record recurring mistakes and update the checklist when a missed step repeats.", "evidence_refs": [evidence[1]]},
                    {"claim_id": "C4", "text": "Keep the workflow bounded to the recurring administrative task rather than mixing unrelated work into one checklist.", "evidence_refs": [evidence[1]]},
                    {"claim_id": "C5", "text": "Use the same structured workflow on later runs so repeated friction can be compared consistently.", "evidence_refs": [evidence[0]]},
                ],
            }

        elif wc.endswith("H-PRODUCT-ARCH"):
            kp = next(x for x in inputs if isinstance(x, dict) and x.get("schema_version") == "die.h03.knowledge-package.v1")
            ids = [c["claim_id"] for c in kp["claims"]]
            payload = {
                "title": "Recurring Admin Workflow Checklist",
                "subtitle": "A repeatable checklist and review loop for recurring digital administrative work",
                "delivery_shape": "QUICK_VERIFY",
                "recurrence": "REPEATED",
                "decision_complexity": "LOW",
                "explanation_depth": "MEDIUM",
                "input_capture": "LIGHT",
                "lookup_frequency": "HIGH",
                "evidence_density": "MEDIUM",
                "reusable_structure": False,
                "section_plan": [
                    {"heading": "Set up the workflow", "claim_ids": ids[:2]},
                    {"heading": "Run the checklist", "claim_ids": ids[2:4]},
                    {"heading": "Review and improve", "claim_ids": ids[4:]},
                ],
            }

        elif "I-PROD-SEC-" in wc:
            bp = next(x for x in inputs if isinstance(x, dict) and x.get("schema_version") == "die.h03.product-blueprint.v1")
            sec_index = int(wc.rsplit("SEC-", 1)[1]) - 1
            sec = bp["sections"][sec_index]
            claim_ids = sec["claim_ids"]
            payload = {"blocks": [
                {"block_id": f"B-{sec_index+1}-1", "kind": "STEP", "text": "Use this section as a practical execution step: follow the supported workflow instruction, mark the step complete, and pause if required information is missing before proceeding.", "claim_ids": [claim_ids[0]]},
                {"block_id": f"B-{sec_index+1}-2", "kind": "CHECKLIST_ITEM", "text": "Before closing this section, verify that the supported claim has been applied to the current workflow and record any repeated error that should change the next run.", "claim_ids": [claim_ids[-1]]},
            ]}

        elif wc.endswith("K-REVIEW"):
            payload = {
                "decision": "PASS",
                "evidence_confidence": "MEDIUM",
                "risk_flags": [],
                "rights_flags": ["Public references are used for factual grounding only; verbatim reuse is not authorized."],
                "decision_reasons": [
                    "The product remains within the accepted evidence-backed claims.",
                    "The package provides a bounded repeatable workflow and does not claim publication authorization.",
                ],
            }
        else:
            raise AssertionError(f"Unhandled fake card: {wc}")

        if payload_validator is not None:
            payload = payload_validator(payload)
        ref = self.courier.commit_payload(
            run_id=run_id,
            artifact_id=f"{wc}-OUT",
            kind=card["output_contract"]["artifact_kind"],
            declared_schema=card["output_contract"]["schema_version"],
            producer_work_card_id=wc,
            payload=payload,
        )
        provider = "claude" if wc.endswith("K-REVIEW") else ("gemini" if wc.endswith("G-SYNTH") else "qwen")
        return {
            "schema_version": "die.h03.cognition-worker-result.v1",
            "work_card_id": wc,
            "status": "SUCCEEDED",
            "attempt": 1,
            "output_artifacts": [ref],
            "worker_observation": {
                "provider_id": provider,
                "effective_model": "TEST-MODEL",
                "effective_mode": "TEST-MODE",
            },
        }


def fake_source_verifier(*, run_id, source_requests, max_sources=12, **kwargs):
    verified = []
    for idx, req in enumerate(source_requests[:max_sources], 1):
        sid = req["source_id"]
        raw_sha = f"{idx:064x}"[-64:]
        text = (
            f"Verified public reference {sid}: recurring workflow friction, structured checklists, "
            "and practical review steps are discussed for this bounded problem."
        )
        if req.get("signal_hint") == "PAID_SUBSTITUTE":
            text += " Pricing plans include a paid subscription at $12 per month."
        if req.get("signal_hint") == "MARKETPLACE_SALE_PROXY":
            text += " The marketplace listing displays customer reviews and ratings."
        verified.append({
            "source_id": sid,
            "source_uri": req["url"],
            "source_class": req["source_class"],
            "candidate_id": req.get("candidate_id"),
            "signal_hint": req.get("signal_hint"),
            "rights_status": "GOVERNED_EXTERNAL",
            "raw_sha256": raw_sha,
            "normalized_text_sha256": f"{idx + 100:064x}"[-64:],
            "acquisition_method": "HTTP_CLIENT",
            "rights_policy": {"state": "REVIEWED_REFERENCE_ONLY", "basis": "test", "verbatim_reuse_allowed": False},
            "review": {"status": "ACCEPTED_FOR_KNOWLEDGE", "reviewer_kind": "GOVERNED_RULESET", "reviewer_id": "TEST", "decision_basis": "test", "crawler_or_llm_authority": False},
            "canonical_truth": False,
            "evidence_units": [{"evidence_id": f"{sid}-E0001", "text": text, "sha256": "c" * 64, "source_raw_sha256": raw_sha}],
        })
    return {
        "schema_version": "die.h03.live-verified-source-bundle.v1",
        "holding_id": "H03",
        "run_id": run_id,
        "verified_sources": verified,
        "failures": [],
        "verified_count": len(verified),
        "requested_count": len(source_requests[:max_sources]),
        "truth_status": "VERIFIED_PUBLIC_REFERENCE_SNAPSHOTS",
    }


class LiveOrgRunnerTests(unittest.TestCase):
    def test_full_mocked_dag_reaches_founder_qc_with_real_pdf_package(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            courier = artifact_courier.ArtifactCourier(root / "artifacts")
            client = FakeClient()
            worker = FakeWorker(courier)
            result = mod.run_live_org(
                artifact_root=root / "artifacts",
                output_root=root / "products",
                founder_qc_root=root / "founder-qc",
                source_verifier=fake_source_verifier,
                courier=courier,
                client=client,
                worker=worker,
            )
            self.assertEqual(result["status"], "WAITING_FOUNDER_QC")
            self.assertEqual(result["worth_making"]["decision"], "MAKE")
            self.assertEqual(result["independent_review"]["decision"], "PASS")
            self.assertFalse(result["external_publication"])
            self.assertFalse(result["founder_publication_gate_crossed"])
            product = result["product"]
            self.assertEqual(product["package_receipt"]["status"], "LOCAL_SALE_READY_UNREVIEWED")
            self.assertGreaterEqual(product["package_receipt"]["page_count"], 1)
            package_dir = root / "products" / product["product_id"]
            self.assertTrue((package_dir / product["package_receipt"]["pdf_file"]).is_file())
            self.assertTrue((package_dir / product["package_receipt"]["zip_file"]).is_file())
            self.assertTrue((root / "founder-qc" / product["product_id"] / "run-summary.json").is_file())
            self.assertIn("H03-WC-LIVE001-G-SYNTH", worker.calls)
            self.assertIn("H03-WC-LIVE001-K-REVIEW", worker.calls)

    def test_market_evaluation_requires_paid_or_marketplace_signal(self):
        bundle = fake_source_verifier(
            run_id="R",
            source_requests=[
                {"source_id": "S1", "url": "https://example.com/1", "source_class": "COMPETITOR_PRODUCT", "candidate_id": "P1", "signal_hint": "PAID_SUBSTITUTE"},
                {"source_id": "S2", "url": "https://example.org/2", "source_class": "SPECIALIST_PUBLICATION", "candidate_id": "P1", "signal_hint": "REPEATED_PAIN"},
            ],
        )
        payload = {
            "selected_problem_seed_id": "P1",
            "pain_observation": {"severity": "MEDIUM", "frequency": "MEDIUM", "urgency": "MEDIUM"},
            "buyer_intent_state": "MEDIUM",
            "productability_state": "HIGH",
            "productability_source_ids": ["S1"],
            "evidence": [
                {"evidence_id": "E1", "signal_type": "REPEATED_PAIN", "source_ids": ["S2"], "rationale": "Repeated pain exists."},
                {"evidence_id": "E2", "signal_type": "ENGAGEMENT_ONLY", "source_ids": ["S2"], "rationale": "Engagement exists but no paid evidence item is selected."},
            ],
            "selection_reasons": ["reason"],
        }
        with self.assertRaisesRegex(ValueError, "WTP_SIGNAL_REQUIRED"):
            mod._validate_market_evaluation(payload, seed_ids={"P1"}, source_bundle=bundle)


    def test_market_source_recovery_r2_resumes_from_existing_a_b_and_reaches_qc(self):
        calls = {"count": 0}

        def recovering_verifier(*, run_id, source_requests, max_sources=12, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                subset = [r for r in source_requests if r.get("signal_hint") != "PAID_SUBSTITUTE"][:1]
                return fake_source_verifier(run_id=run_id, source_requests=subset, max_sources=max_sources)
            return fake_source_verifier(run_id=run_id, source_requests=source_requests, max_sources=max_sources)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            courier = artifact_courier.ArtifactCourier(root / "artifacts")
            client = FakeClient()
            worker = FakeWorker(courier)
            result = mod.run_live_org(
                artifact_root=root / "artifacts", output_root=root / "products",
                founder_qc_root=root / "founder-qc", source_verifier=recovering_verifier,
                courier=courier, client=client, worker=worker,
            )
            self.assertEqual(result["status"], "WAITING_FOUNDER_QC")
            self.assertIn("H03-WC-LIVE001-B2R1-MARKET-RECOVERY", worker.calls)
            self.assertIn("H03-WC-LIVE001-C-R1-MARKET-EVAL", worker.calls)
            eligibility_ref = courier.existing_ref(
                run_id="LIVE-ORG-001", artifact_id="LIVE001-MARKET-ELIGIBILITY", kind="market_eligibility"
            )
            self.assertIsNotNone(eligibility_ref)
            eligibility = courier.resolve(eligibility_ref)
            self.assertTrue(eligibility["eligible_candidates"])
            self.assertTrue(all(item["paid_source_ids"] for item in eligibility["eligible_candidates"]))
            ref = courier.existing_ref(
                run_id="LIVE-ORG-001", artifact_id="LIVE001-MARKET-VERIFIED-SOURCES-R2", kind="verified_source_bundle"
            )
            self.assertIsNotNone(ref)
            merged = courier.resolve(ref)
            self.assertTrue(mod._market_ready_candidate_ids(merged))
            self.assertGreaterEqual(calls["count"], 2)


if __name__ == "__main__":
    unittest.main()
