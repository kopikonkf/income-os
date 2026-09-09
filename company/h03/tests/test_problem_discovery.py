import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "problem_discovery.py"
spec = importlib.util.spec_from_file_location("problem_discovery", P)
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)


class ProblemDiscoveryTests(unittest.TestCase):
    def seed(self, seed_id="H03-PS-A1", actor="freelancer"):
        return {
            "schema_version":"die.h03.human-problem-seed.v1","problem_seed_id":seed_id,"holding_id":"H03",
            "persona":{"actor":actor,"qualifier":"uses many online services"},"context":"manages scattered accounts and settings",
            "trigger":"needs a repeatable cleanup workflow","job_to_be_done":"reduce repeated manual searching and setup friction",
            "pain":{"statement":"instructions are fragmented and inconsistent","severity_state":"UNKNOWN","frequency_state":"UNKNOWN","urgency_state":"UNKNOWN"},
            "desired_outcome":"one actionable sequence with clear checks",
            "commercial_signals":{"demand":{"state":"OBSERVED","evidence_refs":["bad://curator-claim"]},"willingness_to_pay":{"state":"OBSERVED","evidence_refs":["bad://curator-claim"]}},
            "source_refs":["signal://1"],"truth_status":"VALIDATED"
        }

    def test_seed_curator_card_is_web_ai_only_standard_worker(self):
        card = mod.build_seed_curator_work_card(batch_id="B001", signal_artifact_ref="artifact://signals/B001")
        self.assertEqual(card["role"], "SEED_CURATOR")
        self.assertEqual(card["capability_requirements"], {"web_ai":True,"mcp":False,"shell":False,"local_filesystem":False})

    def test_curation_resets_commercial_truth_to_unknown(self):
        seed = mod.normalize_discovered_seed(self.seed())
        self.assertEqual(seed["commercial_signals"]["demand"]["state"], "UNKNOWN")
        self.assertEqual(seed["commercial_signals"]["willingness_to_pay"]["state"], "UNKNOWN")
        self.assertEqual(seed["truth_status"], "CANDIDATE")
        self.assertEqual(seed["source_refs"], ["signal://1"])

    def test_dedupe_uses_problem_semantics_not_seed_id(self):
        a=self.seed("H03-PS-A1"); b=self.seed("H03-PS-A2")
        unique, dupes = mod.deduplicate_problem_seeds([a,b])
        self.assertEqual(len(unique),1); self.assertEqual(dupes,1)

    def test_batch_preserves_signal_lineage(self):
        batch = mod.build_problem_seed_batch(batch_id="B001",source_signal_refs=["artifact://signals/B001"],candidates=[self.seed()])
        self.assertEqual(batch["source_signal_refs"],["artifact://signals/B001"])
        self.assertEqual(batch["truth_status"],"CANDIDATE")
