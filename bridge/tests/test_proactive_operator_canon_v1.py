from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "ORCHESTRATOR_CONTRACT.md"
OPERATIONS = ROOT / "docs" / "operations" / "PROACTIVE_OPERATOR_V1.md"
TICK_SCHEMA = ROOT / "company" / "schemas" / "die.operator.tick.v1.schema.json"
PLATFORM_SCHEMA = (
    ROOT / "company" / "schemas" / "die.platform.receipt.v1.schema.json"
)
COMPANY_BRAIN = ROOT / "COMPANY_BRAIN.md"
HERMES_AGENTS = ROOT / "company" / "die-agents" / "hermes" / "AGENTS.md"
PIPELINE = ROOT / "docs" / "pipeline" / "DIGITAL_INCOME_PIPELINE_CANON.md"
EVENT_WRITER = ROOT / "bin" / "die_event.py"

STATES = {
    "IDLE",
    "RESEARCH_PENDING",
    "BLUEPRINT_PENDING",
    "AWAITING_AUTHORIZATION",
    "BATCH_RUNNING",
    "QA_GATE",
    "FOUNDER_QC",
    "SUBMISSION_WAIT",
    "LEARNING_LOOP",
    "TIER2_ROUTING",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_read(path))


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_required_canon_and_schema_artifacts_are_utf8_readable() -> None:
    for path in (CONTRACT, OPERATIONS, TICK_SCHEMA, PLATFORM_SCHEMA):
        assert path.is_file(), path
        assert _read(path).strip(), path


def test_authority_matrix_separates_autonomous_founder_and_forbidden_actions() -> None:
    contract = _read(CONTRACT)
    flat_contract = _flat(CONTRACT)

    for action in (
        "OP-OBSERVE-STATE",
        "OP-REQUEST-DIVISION01",
        "OP-WRITE-LEARNING",
        "OP-DRAFT-U1-REQUEST",
        "OP-INVOKE-M001-RUNNER",
        "OP-PROPOSE-TIER2",
    ):
        assert action in contract
    for action in (
        "F-FOUNDER-QC",
        "F-PRODUCTION-AUTH",
        "F-SPEND",
        "F-SUBMIT",
        "F-PUBLISH",
        "F-ACCOUNT",
        "F-AUTONOMY",
    ):
        assert action in contract
    for action in (
        "X-DIRECT-STATE-WRITE",
        "X-DIRECT-PROXIMA",
        "X-PROMPT-IMPROVISATION",
        "X-PRODUCTION-CRON",
        "X-AUTO-SOCIAL",
        "X-SELF-PROMOTION",
    ):
        assert action in contract

    assert "m001_loop.py" in contract
    assert "only M-001 production graph materializer" in flat_contract
    assert "`PROPOSE_ONLY` is not observation-only" in contract


def test_operator_state_machine_and_tick_schema_have_exact_same_states() -> None:
    contract = _read(CONTRACT)
    schema_states = set(
        _json(TICK_SCHEMA)["$defs"]["operator_state"]["enum"]
    )

    assert schema_states == STATES
    for state in STATES:
        assert f"`{state}`" in contract


def test_tick_schema_is_propose_only_zero_cost_and_bounded() -> None:
    schema = _json(TICK_SCHEMA)
    properties = schema["properties"]

    assert properties["schema_version"]["const"] == "die.operator.tick.v1"
    assert properties["mode"]["enum"] == ["PROPOSE_ONLY"]
    assert properties["operator_id"]["const"] == "hermes-operator"
    assert properties["mission_id"]["const"] == "M-001"
    assert properties["mutations"]["maxItems"] == 3
    assert properties["budget"]["properties"]["cost_usd"]["const"] == 0
    assert properties["budget"]["properties"]["input_bytes"]["maximum"] == 24576
    assert properties["budget"]["properties"]["output_tokens"]["maximum"] == 1800
    assert properties["budget"]["properties"]["wall_time_seconds"]["maximum"] == 480
    for field in ("source_snapshot", "candidate_actions", "event_dedupe_key"):
        assert field in schema["required"]


def test_platform_receipt_is_route_specific_and_simulation_safe() -> None:
    schema = _json(PLATFORM_SCHEMA)
    properties = schema["properties"]

    assert properties["schema_version"]["const"] == "die.platform.receipt.v1"
    assert set(properties["platform"]["enum"]) == {
        "ADOBE_STOCK",
        "DREAMSTIME",
        "123RF",
        "VECTEEZY",
        "MOTIONELEMENTS",
    }
    assert "SIMILAR_CONTENT" in properties["reason_code"]["enum"]
    assert "RIGHTS" in properties["reason_code"]["enum"]
    assert "SYNTHETIC" in properties["evidence_label"]["enum"]
    synthetic = schema["allOf"][0]
    assert synthetic["then"]["properties"]["recorded_by"]["const"] == (
        "simulation-fixture"
    )
    assert synthetic["then"]["properties"]["cost_usd"]["const"] == 0


def test_tick_uses_existing_event_writer_and_one_event_even_for_no_op() -> None:
    contract = _read(CONTRACT)
    operations = _read(OPERATIONS)
    writer = _read(EVENT_WRITER)

    assert "including `NO_OP` ticks" in contract
    assert "WRITE tick receipt" in operations
    assert "COMMIT one event through die_event.py" in operations
    assert "--detail-ref" in contract
    assert 'event_parser.add_argument("--detail-ref")' in writer
    assert 'event_parser.add_argument("--dedupe-key")' in writer


def test_cognitive_cron_is_not_a_production_cron_or_second_control_plane() -> None:
    operations = _read(OPERATIONS)
    flat_operations = _flat(OPERATIONS)

    assert "`*/30 * * * *`" in operations
    assert "`no_agent=false`" in operations
    assert (
        "Existing deterministic crons remain `no_agent=true` and unchanged."
        in flat_operations
    )
    assert "It adds neither a second orchestrator nor a production scheduler." in operations
    assert "`m001_loop.py` remains the only M-001 J1–J8 materializer" in operations
    assert "one tick at a time; overlap denied" in operations.lower()


def test_founder_notification_budget_quiet_hours_and_kill_switch_are_canon() -> None:
    contract = _read(CONTRACT)
    operations = _read(OPERATIONS)
    flat_operations = _flat(OPERATIONS)

    assert "AUTHORIZATION_REQUIRED" in contract
    assert "FOUNDER_QC_READY" in contract
    assert "maximum four wakes/day" in operations
    assert "22:00–07:00 Asia/Bangkok" in operations
    assert "/die_pause_operator" in operations
    assert "/die_resume_operator" in operations
    assert "The LLM cannot ignore, override, or clear the pause itself." in flat_operations


def test_learning_and_tier2_routes_do_not_bypass_rights_or_pillar_authority() -> None:
    operations = _read(OPERATIONS)
    flat_operations = _flat(OPERATIONS)
    pipeline = _read(PIPELINE)

    assert "A platform receipt is an observation, not automatically a causal diagnosis." in operations
    assert "new blueprint hash and requires new Founder production authority" in (
        flat_operations
    )
    assert "If every submitted route in a batch is rejected" in operations
    assert "does not regenerate or reuse the prior production authorization" in (
        flat_operations
    )
    assert "Pillar A is currently `FUTURE`" in operations
    assert "no failure automatically becomes public content" in operations
    assert "Residual-ready inventory is not automatically published." in pipeline


def test_company_brain_and_hermes_boot_require_proactive_canon() -> None:
    brain = _read(COMPANY_BRAIN)
    hermes = _read(HERMES_AGENTS)
    flat_hermes = _flat(HERMES_AGENTS)

    for document in (
        "ORCHESTRATOR_CONTRACT.md",
        "docs/operations/PROACTIVE_OPERATOR_V1.md",
    ):
        assert document in brain
        assert document in hermes
    assert "every proactive operational tick" in brain
    assert "one `die.operator.tick.v1` receipt" in hermes
    assert "only permitted prompt cron" in flat_hermes
    assert "Pillar A remains FUTURE" in hermes


def test_canon_pr_declares_runtime_implementation_as_later_owner() -> None:
    operations = _read(OPERATIONS)

    assert "runtime implementation pending OpenCode integration" in operations
    assert "After canon merge, OpenCode—not Architect DEV cognition—implements" in operations
    assert "No runtime job, cron, service, account, production request" in operations
