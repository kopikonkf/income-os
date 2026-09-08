from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
G=ROOT/"company/factory-asset/task-graph-v1.json"
R=ROOT/"company/factory-asset/receipts/FA-SCALE-20260907-capacity-network-discovery.receipt.json"

def test_scale_foundation_nodes_follow_fa307_dependency_lifecycle():
 g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]}
 fa307_done=by["FA-307"]["status"]=="DONE"
 for i in range(310,315):
  t=by[f"FA-{i}"];assert t["track"]=="SCALE_FOUNDATION" and "FA-307" in t["depends_on"]
  assert t["status"] in ({"READY","IN_PROGRESS","DONE"} if fa307_done else {"BLOCKED"})
 assert by["FA-315"]["status"]=="BLOCKED" and set(by["FA-315"]["depends_on"])=={f"FA-{i}" for i in range(310,315)}

def test_fa308_requires_scale_foundation_gate_and_never_equates_profiles_with_live_browsers():
 g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]};t=by["FA-308"]
 assert {"FA-127","FA-307","FA-315"}.issubset(set(t["depends_on"]))
 assert "100 persistent profiles must never be treated as 100 concurrently-running Chromium owners" in t["acceptance"]

def test_discovery_receipt_separates_measured_facts_from_planning_scenarios():
 d=json.loads(R.read_text());o=d["observed"];s=d["planning_scenarios_not_observed_capacity"]
 assert o["persistent_profiles_mib"]=={"chatgpt-linux-a":341,"web-ai-cluster-b":349,"measured_average":345}
 assert o["shared_runtime_mib"]["playwright_chromium"]==656
 assert o["fa307_attempt1"]["combined_browser_tree_peak_mib"]==4739.25
 assert s["100_profiles_current_plus_shared_runtime_mib"]==35201
 assert s["100_profiles_at_1_gib_each_gib"]==100 and s["100_profiles_at_2_gib_each_gib"]==200

def test_cloudflare_boundary_and_network_cutover_remain_fail_closed():
 d=json.loads(R.read_text());c=d["observed"]["cloudflare_boundary"];a=d["authority"]
 assert c["cdp_route_exposed"] is False and c["browser_wake_route_exposed"] is False and c["cluster_broker_route_exposed"] is False
 assert a["network_cutover_authorized"] is False and a["spend_authorized"] is False

def test_hermes_multicluster_wiring_is_required_before_pre1k_gate():
 g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]}
 assert by["FA-313"]["title"]=="Wire Hermes production runtime to governed multi-cluster scheduler"
 assert "FA-313" in by["FA-315"]["depends_on"] and "FA-315" in by["FA-308"]["depends_on"]
