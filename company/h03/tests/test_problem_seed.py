import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "problem_seed.py"
spec = importlib.util.spec_from_file_location("problem_seed", P)
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)


class ProblemSeedTests(unittest.TestCase):
    def seed(self):
        return {
            "schema_version": mod.SCHEMA,
            "problem_seed_id": "H03-PS-PRIVACY_001",
            "holding_id": "H03",
            "persona": {"actor": "consumer", "qualifier": "uses several consumer web services"},
            "context": "manages accounts across major online services",
            "trigger": "wants to reduce unnecessary personal-data exposure",
            "job_to_be_done": "systematically review and reduce stored personal information",
            "pain": {"statement": "deletion and privacy controls are fragmented across services", "severity_state": "UNKNOWN", "frequency_state": "UNKNOWN", "urgency_state": "UNKNOWN"},
            "desired_outcome": "one reliable sequence for reviewing and reducing exposure",
            "commercial_signals": {"demand": {"state": "UNKNOWN", "evidence_refs": []}, "willingness_to_pay": {"state": "UNKNOWN", "evidence_refs": []}},
            "source_refs": [],
            "truth_status": "CANDIDATE"
        }

    def test_complete_problem_seed_passes_with_unknown_commercial_truth(self):
        self.assertEqual(mod.validate_problem_seed(self.seed())["truth_status"], "CANDIDATE")

    def test_topic_only_seed_fails(self):
        seed = self.seed(); seed["job_to_be_done"] = ""
        with self.assertRaisesRegex(ValueError, "PROBLEM_SEED_FIELD_REQUIRED"):
            mod.validate_problem_seed(seed)

    def test_non_unknown_demand_requires_evidence(self):
        seed = self.seed(); seed["commercial_signals"]["demand"] = {"state": "OBSERVED", "evidence_refs": []}
        with self.assertRaisesRegex(ValueError, "OBSERVED_SIGNAL_NEEDS_EVIDENCE"):
            mod.validate_problem_seed(seed)

    def test_unknown_wtp_cannot_carry_fake_evidence(self):
        seed = self.seed(); seed["commercial_signals"]["willingness_to_pay"] = {"state": "UNKNOWN", "evidence_refs": ["fake"]}
        with self.assertRaisesRegex(ValueError, "UNKNOWN_SIGNAL_HAS_EVIDENCE"):
            mod.validate_problem_seed(seed)
