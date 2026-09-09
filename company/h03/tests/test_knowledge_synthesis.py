import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "knowledge_synthesis.py"
spec = importlib.util.spec_from_file_location("knowledge_synthesis", P)
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

HP = ROOT / "company" / "h03" / "lib" / "h03_factory.py"
hspec = importlib.util.spec_from_file_location("h03_factory_synth_test", HP)
h03 = importlib.util.module_from_spec(hspec); assert hspec.loader; hspec.loader.exec_module(h03)


class KnowledgeSynthesisTests(unittest.TestCase):
    def packet(self, packet_id, source_id, evidence_id, text, provider="qwen", governed=False):
        source = {
            "schema_version":"die.h03.external-source-snapshot.v1",
            "source_id":source_id,
            "source_uri":f"https://example.invalid/{source_id}",
            "media_type":"text/plain",
            "acquisition_method":"WEB_TOOL_SNAPSHOT",
            "raw_sha256":"a"*64,
            "normalized_text_sha256":"b"*64,
            "review_state":"PENDING_REVIEW",
            "canonical_truth":False,
            "rights_policy":{"state":"UNKNOWN","basis":"","verbatim_reuse_allowed":False},
            "evidence_units":[{"evidence_id":evidence_id,"text":text,"raw_source_sha256":"a"*64}]
        }
        if governed:
            source.pop("review_state", None)
            source["rights_policy"]={"state":"REVIEWED_REFERENCE_ONLY","basis":"governed test","verbatim_reuse_allowed":False}
            source["review"]={"status":"ACCEPTED_FOR_KNOWLEDGE","reviewer_kind":"GOVERNED_RULESET","reviewer_id":"test-rule","decision_basis":"test","crawler_or_llm_authority":False}
        return {
            "schema_version":"die.h03.research-packet.v1",
            "research_packet_id":packet_id,
            "holding_id":"H03",
            "work_card_id":f"WC-{packet_id}",
            "question_id":f"Q-{packet_id}",
            "provider_observation":{"provider_id":provider},
            "source_snapshots":[source],
            "findings":[{"finding_id":f"F-{packet_id}","text":text,"evidence_refs":[evidence_id]}],
            "terminal_status":"SUCCEEDED",
            "truth_status":"UNVERIFIED_RESEARCH_PACKET"
        }

    def artifacts(self):
        return [
            {"artifact_id":"RP-1","kind":"research_packet","ref":"artifact://research/RP-1","sha256":None},
            {"artifact_id":"RP-2","kind":"research_packet","ref":"artifact://research/RP-2","sha256":None},
        ]

    def model_output(self):
        return {
            "supported_findings":[{"finding_id":"SF-1","text":"A paid substitute exists for the problem.","evidence_refs":["E-1"]}],
            "contradictions":[],
            "gaps":[],
            "market_wtp_findings":[{"finding_id":"MW-1","text":"The market contains a paid substitute.","evidence_refs":["E-1"],"signal_type":"PAID_SUBSTITUTE"}],
            "claims":[{"claim_id":"C-1","text":"A structured workflow can remove search and sequencing friction.","evidence_refs":["E-2"]}]
        }

    def test_synthesis_work_card_is_standard_web_ai_worker(self):
        card=mod.build_synthesis_work_card(knowledge_map_id="KM-001",research_packet_artifacts=self.artifacts())
        self.assertEqual(card["role"],"SYNTHESIZER")
        self.assertEqual(card["capability_requirements"],{"web_ai":True,"mcp":False,"shell":False,"local_filesystem":False})
        req=mod.build_synthesis_request(card=card,packets=[self.packet("RP-1","SRC-1","E-1","Paid substitute evidence."),self.packet("RP-2","SRC-2","E-2","Workflow evidence.")],model_route="qwen/qwen3.8-max")
        self.assertEqual(req["role"],"SYNTHESIZER")
        self.assertNotIn("source_snapshots",str(req["context"]))

    def test_supported_synthesis_remains_noncanonical_pending_source_governance(self):
        packets=[self.packet("RP-1","SRC-1","E-1","Paid substitute evidence."),self.packet("RP-2","SRC-2","E-2","Workflow evidence.")]
        km,candidate=mod.normalize_synthesis_output(knowledge_map_id="KM-001",candidate_id="KPC-001",packets=packets,model_output=self.model_output())
        self.assertEqual(km["truth_status"],"UNVERIFIED_SYNTHESIS")
        self.assertFalse(candidate["canonical_truth"])
        self.assertEqual(candidate["promotion_state"],"AWAITING_SOURCE_GOVERNANCE")
        with self.assertRaisesRegex(ValueError,"KNOWLEDGE_SCHEMA_INVALID"):
            h03.validate_knowledge_package(candidate)

    def test_unknown_evidence_ref_fails_closed(self):
        packets=[self.packet("RP-1","SRC-1","E-1","Paid substitute evidence."),self.packet("RP-2","SRC-2","E-2","Workflow evidence.")]
        out=self.model_output(); out["claims"][0]["evidence_refs"]=["E-MISSING"]
        with self.assertRaisesRegex(ValueError,"SYNTHESIS_UNRESOLVED_EVIDENCE"):
            mod.normalize_synthesis_output(knowledge_map_id="KM-001",candidate_id="KPC-001",packets=packets,model_output=out)

    def test_critical_gap_precedes_source_governance(self):
        packets=[self.packet("RP-1","SRC-1","E-1","Paid substitute evidence."),self.packet("RP-2","SRC-2","E-2","Workflow evidence.")]
        out=self.model_output(); out["gaps"]=[{"gap_id":"G-1","question":"What critical procedure remains unverified?","critical":True}]
        _,candidate=mod.normalize_synthesis_output(knowledge_map_id="KM-002",candidate_id="KPC-002",packets=packets,model_output=out)
        self.assertEqual(candidate["promotion_state"],"AWAITING_GAP_RESOLUTION")

    def test_unresolved_contradiction_precedes_source_governance(self):
        packets=[self.packet("RP-1","SRC-1","E-1","Source A says one procedure."),self.packet("RP-2","SRC-2","E-2","Source B says another procedure.")]
        out=self.model_output(); out["contradictions"]=[{"contradiction_id":"X-1","statement":"Sources disagree on the procedure.","evidence_refs":["E-1","E-2"],"resolution_state":"UNRESOLVED"}]
        _,candidate=mod.normalize_synthesis_output(knowledge_map_id="KM-003",candidate_id="KPC-003",packets=packets,model_output=out)
        self.assertEqual(candidate["promotion_state"],"AWAITING_CONTRADICTION_RESOLUTION")

    def test_governed_sources_without_gaps_or_contradictions_become_validation_eligible_only(self):
        packets=[self.packet("RP-1","SRC-1","E-1","Paid substitute evidence.",governed=True),self.packet("RP-2","SRC-2","E-2","Workflow evidence.",governed=True)]
        _,candidate=mod.normalize_synthesis_output(knowledge_map_id="KM-004",candidate_id="KPC-004",packets=packets,model_output=self.model_output())
        self.assertEqual(candidate["promotion_state"],"ELIGIBLE_FOR_KNOWLEDGE_VALIDATION")
        self.assertFalse(candidate["canonical_truth"])
