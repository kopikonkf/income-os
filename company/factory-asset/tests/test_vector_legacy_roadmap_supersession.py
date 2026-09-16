import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH = ROOT / "company/factory-asset/task-graph-v1.json"

def test_legacy_fav_roadmap_is_closed_as_superseded():
    g=json.loads(GRAPH.read_text(encoding="utf-8")); by={t["id"]:t for t in g["tasks"]}
    expected={
        "FA-V001":"FA-320", "FA-V002":"FA-321", "FA-V003":"H01-107,H01-108", "FA-V004":"FA-321",
        "FA-V005":"H01-115,H01-134", "FA-V006":"H01-134,H01-135", "FA-V007":"H01-134",
    }
    for tid,succ in expected.items():
        assert by[tid]["status"]=="DONE"
        assert by[tid]["result"].startswith("SUPERSEDED:")
        assert by[tid]["superseded_by"]==succ

def test_fa322_is_closed_by_separate_v2_svg_evidence():
    g=json.loads(GRAPH.read_text(encoding="utf-8")); by={t["id"]:t for t in g["tasks"]}
    assert by["FA-320"]["status"]=="DONE"
    assert by["FA-321"]["status"]=="DONE"
    assert by["FA-322"]["status"]=="DONE"
    assert by["FA-322"]["superseded_by"]=="H01-107,H01-108"
    assert "Factory Asset V2 owns the SVG production engine" in by["FA-322"]["result"]
