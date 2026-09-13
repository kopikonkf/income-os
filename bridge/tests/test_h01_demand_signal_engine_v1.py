from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / "company" / "company-os" / "die-h01"
DOC = H01 / "DIE_H01_DEMAND_SIGNAL_ENGINE_V1.md"
SCHEMA = H01 / "contracts" / "h01-demand-signal-ranking.v1.schema.json"
FIXTURES = H01 / "fixtures" / "h01-demand-signal-ranking.examples.json"
VALIDATOR = H01 / "lib" / "demand_signal_contract.py"
GRAPH = H01 / "die-h01-task-graph.v1.json"


def _validator():
    spec = importlib.util.spec_from_file_location("h01_demand_signal_contract", VALIDATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _records():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))["records"]


def test_examples_validate():
    v = _validator()
    assert all(v.validate_record(row) == [] for row in _records())


def test_schema_pins_non_blocking_effects_and_zero_authority():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    effects = schema["properties"]["effects"]["properties"]
    assert all(node["const"] == "NONE" for node in effects.values())
    authority = schema["properties"]["authority"]["properties"]
    assert all(node["const"] is False for node in authority.values())


def test_no_evidence_remains_unranked():
    row = _records()[0]
    assert row["signal_state"] == "NO_EVIDENCE"
    assert row["rank_state"] == "UNRANKED"
    assert row["rank_score"] is None


def test_ranked_example_has_fresh_evidence():
    row = _records()[1]
    assert row["rank_state"] == "RANKED"
    assert any(e["freshness"] == "FRESH" for e in row["evidence_refs"])


def test_discoveries_are_hypotheses():
    row = _records()[1]
    assert row["discoveries"]["buyers"][0]["status"] == "HYPOTHESIS"
    assert row["discoveries"]["use_cases"][0]["status"] == "HYPOTHESIS"
    assert row["discoveries"]["family_hypotheses"][0]["status"] == "HYPOTHESIS"


def test_contract_is_non_blocking_and_connector_neutral():
    text = DOC.read_text(encoding="utf-8")
    assert "optional ranking and discovery overlay" in text
    assert "This contract authorizes no connector" in text
    assert "missing connectors cannot block standalone production" in text
    assert "Cartesian expansion is not required" in text


def test_graph_progression():
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    by = {row["id"]: row for row in graph["tasks"]}
    assert by["H01-130"]["status"] == "DONE"
    assert by["H01-131"]["status"] in {"READY", "DONE"}
    assert by["H01-132"]["status"] in {"READY", "DONE"}
