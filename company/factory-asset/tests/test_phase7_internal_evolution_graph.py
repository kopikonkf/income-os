import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH = ROOT / "company/factory-asset/task-graph-v1.json"


def _graph():
    return json.loads(GRAPH.read_text(encoding="utf-8"))


def test_phase7_internal_evolution_tasks_are_canonical_and_unique():
    g = _graph()
    rows = [t for t in g["tasks"] if t["id"].startswith("FA-") and t["id"][3:].isdigit()]
    ids = [t["id"] for t in rows]
    assert len(ids) == len(set(ids))
    by = {t["id"]: t for t in rows}
    for n in range(316, 337):
        assert f"FA-{n}" in by
        assert by[f"FA-{n}"]["phase"] == 7


def test_phase7_frontier_after_prompt_foundation():
    g = _graph()
    by = {t["id"]: t for t in g["tasks"]}
    for tid in ["FA-316", "FA-317", "FA-333", "FA-334", "FA-335", "FA-336"]:
        assert by[tid]["status"] == "DONE"
    assert by["FA-318"]["status"] == "DONE"
    assert by["FA-319"]["status"] == "DONE"
    assert by["FA-320"]["status"] == "READY"
    assert by["FA-323"]["status"] == "READY"
    assert by["FA-329"]["status"] == "READY"
    assert "FA-336" in by["FA-318"]["depends_on"]
    assert by["FA-334"]["depends_on"] == ["FA-317", "FA-333"]
    assert by["FA-335"]["depends_on"] == ["FA-334"]
    assert by["FA-336"]["depends_on"] == ["FA-335"]


def test_scale_gate_remains_held_and_phase7_grants_no_scale_authority():
    g = _graph()
    by = {t["id"]: t for t in g["tasks"]}
    assert by["FA-125"]["status"] == "WAITING_FOUNDER"
    assert by["FA-126"]["status"] == "DEFERRED"
    for n in range(316, 337):
        text = (by[f"FA-{n}"].get("acceptance") or "").lower()
        if n in {318, 319, 328, 332}:
            assert "100/day" in text or "scale_100_per_day=false" in text or "throughput scale" in text


def test_new_tracks_are_declared_and_human_atlas_bridge_is_sparse():
    g = _graph()
    tracks = set(g["tracks"])
    assert {"PRODUCTION_BASELINE", "NATIVE_VECTOR", "FOUNDER_OBSERVABILITY", "PROFILE_POOL", "PRODUCTION_INTELLIGENCE", "PROMPT_COMPILER"} <= tracks
    by = {t["id"]: t for t in g["tasks"]}
    assert "without exhaustive Cartesian enumeration" in by["FA-329"]["acceptance"]
    assert "force_all_modes=false" in by["FA-330"]["acceptance"]
    assert "packaging derivatives remain identity-neutral" in by["FA-331"]["acceptance"]
