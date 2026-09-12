import copy
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "company/company-os/die-h01/engineering/graph_width_planner.py"
SPEC = importlib.util.spec_from_file_location("h01_graph_width_planner", MODULE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def done(task_id: str) -> dict:
    return {"id": task_id, "status": "DONE", "authority": "ARCHITECT", "depends_on": []}


class GraphWidthPlannerTests(unittest.TestCase):
    def test_dependency_ready_width_and_unknown_dependency_fail_closed(self):
        graph = {
            "tasks": [
                done("H01-ROOT"),
                {"id": "H01-B", "status": "READY", "authority": "ARCHITECT", "depends_on": ["H01-ROOT"]},
                {"id": "H01-C", "status": "READY", "authority": "ARCHITECT", "depends_on": ["H01-ROOT"]},
                {"id": "H01-D", "status": "READY", "authority": "ARCHITECT", "depends_on": ["H01-B"]},
                {"id": "H01-UNKNOWN", "status": "READY", "authority": "ARCHITECT", "depends_on": ["NOPE"]},
            ]
        }
        plan = M.plan_graph_width(graph)
        self.assertEqual(plan["selected_task_ids"], ["H01-B", "H01-C"])
        self.assertEqual(plan["excluded"]["H01-D"]["code"], "DEPENDENCY_NOT_DONE")
        self.assertEqual(plan["excluded"]["H01-UNKNOWN"]["code"], "UNKNOWN_DEPENDENCY_STATE")

    def test_active_resource_lease_excludes_task(self):
        graph = {"tasks": [
            {"id": "H01-A", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "resources": ["browser-a"]},
            {"id": "H01-B", "status": "READY", "authority": "ARCHITECT", "depends_on": []},
        ]}
        plan = M.plan_graph_width(graph, active_leases=[{"resource": "browser-a", "status": "ACTIVE", "task_id": "OTHER"}])
        self.assertEqual(plan["selected_task_ids"], ["H01-B"])
        self.assertEqual(plan["excluded"]["H01-A"]["code"], "ACTIVE_LEASE_CONFLICT")

    def test_active_worktree_and_candidate_worktree_collisions_fail_closed(self):
        graph = {"tasks": [
            {"id": "H01-A", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "worktree": "/tmp/h01/shared"},
            {"id": "H01-B", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "worktree": "/tmp/h01/shared"},
            {"id": "H01-C", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "worktree": "/tmp/h01/claimed"},
        ]}
        plan = M.plan_graph_width(
            graph,
            active_worktrees=[{"worktree": "/tmp/h01/claimed", "status": "CLAIMED", "task_id": "OTHER"}],
        )
        self.assertEqual(plan["selected_task_ids"], ["H01-A"])
        self.assertEqual(plan["excluded"]["H01-B"]["code"], "WORKTREE_COLLISION")
        self.assertEqual(plan["excluded"]["H01-C"]["code"], "ACTIVE_WORKTREE_CONFLICT")

    def test_shared_mutable_repo_write_collision_and_ambiguous_owner(self):
        graph = {"tasks": [
            {"id": "H01-A", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "mutable_repo_write": True, "repo_write_owner": "H01-A"},
            {"id": "H01-B", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "mutable_repo_write": True, "repo_write_owner": "H01-B"},
            {"id": "H01-C", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "mutable_repo_write": True},
        ]}
        plan = M.plan_graph_width(graph)
        self.assertEqual(plan["selected_task_ids"], ["H01-A"])
        self.assertEqual(plan["excluded"]["H01-B"]["code"], "RESOURCE_COLLISION")
        self.assertEqual(plan["excluded"]["H01-C"]["code"], "AMBIGUOUS_MUTABLE_REPO_WRITE_OWNERSHIP")

    def test_founder_gate_requires_exact_task_authorization(self):
        graph = {"tasks": [
            {"id": "H01-F", "status": "READY", "authority": "FOUNDER_REQUIRED", "depends_on": []},
            {"id": "H01-A", "status": "READY", "authority": "ARCHITECT", "depends_on": []},
        ]}
        self.assertEqual(M.plan_graph_width(graph)["selected_task_ids"], ["H01-A"])
        plan = M.plan_graph_width(graph, founder_authorized_tasks={"H01-F": True})
        self.assertEqual(plan["selected_task_ids"], ["H01-A", "H01-F"])

    def test_ordering_is_deterministic_and_width_is_bounded(self):
        graph = {"tasks": [
            {"id": "H01-Z", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "priority": 1},
            {"id": "H01-A", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "priority": 10},
            {"id": "H01-B", "status": "READY", "authority": "ARCHITECT", "depends_on": [], "priority": 10},
        ]}
        first = M.plan_graph_width(graph, max_workers=2)
        second = M.plan_graph_width(dict(graph), max_workers=2)
        self.assertEqual(first["selected_task_ids"], ["H01-A", "H01-B"])
        self.assertEqual(first["selected_task_ids"], second["selected_task_ids"])
        self.assertEqual(first["excluded"]["H01-Z"]["code"], "WIDTH_LIMIT")

    def test_planner_has_no_durable_state_mutation(self):
        graph = {"tasks": [{"id": "H01-A", "status": "READY", "authority": "ARCHITECT", "depends_on": []}]}
        before = copy.deepcopy(graph)
        plan = M.plan_graph_width(graph)
        self.assertEqual(graph, before)
        self.assertTrue(plan["read_only"])
        self.assertTrue(plan["mission_control_is_scheduler"])
        self.assertFalse(plan["scheduler_action_taken"])
        self.assertFalse(plan["durable_state_mutated"])
        self.assertFalse(plan["canonical_graph_mutated"])

    def test_malformed_coordination_snapshot_fails_closed(self):
        graph = {"tasks": [{"id": "H01-A", "status": "READY", "authority": "ARCHITECT", "depends_on": []}]}
        with self.assertRaisesRegex(M.GraphWidthPlanningError, "E_ACTIVE_LEASE_STATE_UNKNOWN"):
            M.plan_graph_width(graph, active_leases=[{"resource": "browser-a", "status": "MAYBE"}])


if __name__ == "__main__":
    unittest.main()
