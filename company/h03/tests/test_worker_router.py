import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "worker_router.py"
spec = importlib.util.spec_from_file_location("worker_router", P)
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
REG = json.loads((ROOT/"company"/"h03"/"runtime"/"provider-worker-registry.v1.json").read_text(encoding="utf-8"))


class WorkerRouterTests(unittest.TestCase):
    def test_registry_has_qwen_and_gemini_first_class_research_and_production(self):
        mod.validate_registry(REG)
        by={p["provider_id"]:p for p in REG["providers"]}
        for pid in ("qwen","gemini"):
            self.assertIn("KNOWLEDGE_RESEARCHER", by[pid]["roles"])
            self.assertIn("PRODUCER", by[pid]["roles"])
            self.assertIn("SEED_CURATOR", by[pid]["roles"])

    def test_manus_is_autonomous_research_candidate(self):
        manus=next(p for p in REG["providers"] if p["provider_id"]=="manus")
        self.assertIn("KNOWLEDGE_RESEARCHER",manus["roles"])
        self.assertIn("autonomous_browse",manus["capabilities"])

    def test_qwen_selected_when_ready_then_gemini_fallback(self):
        status={"qwen":{"state":"READY","available_slots":1,"profile_shard_id":"knowledge-a"},"gemini":{"state":"READY","available_slots":1,"profile_shard_id":"knowledge-a"}}
        pick=mod.route_worker(role="KNOWLEDGE_RESEARCHER",registry=REG,runtime_status=status,required_capabilities=["web_research"])
        self.assertEqual(pick["provider_id"],"qwen")
        status["qwen"]={"state":"UNAVAILABLE","available_slots":0,"profile_shard_id":"knowledge-a"}
        pick=mod.route_worker(role="KNOWLEDGE_RESEARCHER",registry=REG,runtime_status=status,required_capabilities=["web_research"])
        self.assertEqual(pick["provider_id"],"gemini")

    def test_capacity_zero_is_not_selected(self):
        status={"qwen":{"state":"READY","available_slots":0,"profile_shard_id":"knowledge-a"},"gemini":{"state":"READY","available_slots":2,"profile_shard_id":"knowledge-b"}}
        pick=mod.route_worker(role="PRODUCER",registry=REG,runtime_status=status,required_capabilities=["text_generation"])
        self.assertEqual(pick["provider_id"],"gemini")
        self.assertEqual(pick["profile_shard_id"],"knowledge-b")

    def test_no_healthy_slot_is_typed_failure(self):
        with self.assertRaisesRegex(RuntimeError,"NO_ELIGIBLE_WORKER_SLOT"):
            mod.route_worker(role="PRODUCER",registry=REG,runtime_status={},required_capabilities=["text_generation"])
