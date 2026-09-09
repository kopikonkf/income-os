import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "demand_wtp.py"
spec = importlib.util.spec_from_file_location("demand_wtp", P)
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)


class DemandWTPTests(unittest.TestCase):
    def packet(self, evidence=None, assessment="UNKNOWN"):
        return {
            "schema_version":mod.SCHEMA,"packet_id":"H03-DMD-PKT-001","holding_id":"H03","problem_seed_id":"H03-PS-PRIVACY_001",
            "pain_observation":{"severity":"UNKNOWN","frequency":"UNKNOWN","urgency":"UNKNOWN"},"buyer_intent_state":"UNKNOWN",
            "evidence": evidence or [], "wtp_assessment":assessment,"truth_status":"CANDIDATE"
        }

    def test_no_evidence_preserves_unknown_wtp(self):
        self.assertEqual(mod.validate_demand_packet(self.packet())["wtp_assessment"], "UNKNOWN")

    def test_engagement_only_does_not_become_wtp(self):
        evidence=[{"evidence_id":"E1","signal_type":"ENGAGEMENT_ONLY","evidence_refs":["source://likes"],"money":None}]
        self.assertEqual(mod.derive_wtp_assessment(evidence), "UNKNOWN")
        mod.validate_demand_packet(self.packet(evidence,"UNKNOWN"))

    def test_revealed_spend_is_strong_and_requires_money(self):
        evidence=[{"evidence_id":"E2","signal_type":"REVEALED_SPEND","evidence_refs":["source://receipt"],"money":{"currency":"USD","amount_minor":900}}]
        self.assertEqual(mod.derive_wtp_assessment(evidence), "STRONG")
        mod.validate_demand_packet(self.packet(evidence,"STRONG"))
        evidence[0]["money"]=None
        with self.assertRaisesRegex(ValueError,"REVEALED_SPEND_MONEY_REQUIRED"):
            mod.validate_demand_packet(self.packet(evidence,"STRONG"))

    def test_paid_substitute_or_marketplace_proxy_is_medium(self):
        for signal in ("PAID_SUBSTITUTE","MARKETPLACE_SALE_PROXY"):
            evidence=[{"evidence_id":"E3","signal_type":signal,"evidence_refs":["source://market"],"money":None}]
            self.assertEqual(mod.derive_wtp_assessment(evidence), "MEDIUM")
            mod.validate_demand_packet(self.packet(evidence,"MEDIUM"))

    def test_mismatched_assessment_fails(self):
        evidence=[{"evidence_id":"E4","signal_type":"PURCHASE_INTENT_SEARCH","evidence_refs":["source://search"],"money":None}]
        with self.assertRaisesRegex(ValueError,"WTP_MISMATCH:WEAK"):
            mod.validate_demand_packet(self.packet(evidence,"STRONG"))
