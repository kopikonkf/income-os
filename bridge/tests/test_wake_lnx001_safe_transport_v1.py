from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "company" / "browser" / "linux" / "wake_transport_core.mjs"
EXEC = ROOT / "company" / "executive" / "linux" / "wake_transport.mjs"
DIV = ROOT / "company" / "division" / "division001" / "linux" / "wake_transport.mjs"
DOC = ROOT / "docs" / "architecture" / "DIE_LINUX_SAFE_WAKE_TRANSPORT_V1.md"


def test_wake_transport_has_no_private_backend_or_secret_extraction_surface() -> None:
    text = CORE.read_text(encoding="utf-8")
    forbidden = ["/backend-api", "/api/auth/session", "localStorage", "sessionStorage", ".cookies(", "document.cookie", "sentinel", "proof-of-work", "keyboard.press", ".click()"]
    for token in forbidden:
        assert token not in text
    assert "submitted: false" in text
    assert "output_extracted: false" in text
    assert "credential_material_accessed: false" in text
    assert "private_backend_called: false" in text
    assert "127.0.0.1" in text
    assert "browser.close()" not in text


def test_principal_wrappers_are_linux_instance_pinned() -> None:
    assert "die-lnx-executive-001" in EXEC.read_text(encoding="utf-8")
    assert "process.exit(0)" in EXEC.read_text(encoding="utf-8")
    assert "die-lnx-division-001" in DIV.read_text(encoding="utf-8")
    assert "process.exit(0)" in DIV.read_text(encoding="utf-8")
    assert "aethers.web.id" not in EXEC.read_text(encoding="utf-8") + DIV.read_text(encoding="utf-8")


def test_node_pure_thread_state_and_envelope_contract() -> None:
    source = f'''import {{normalizeThreadUrl, validateEnvelope, updateThreadState}} from {json.dumps(CORE.as_uri())};
const t=normalizeThreadUrl('https://chatgpt.com/c/abc-123');
const env=validateEnvelope({{schema:'die.wake.envelope.v1',company_instance_id:'DIE-LINUX',principal_id:'die-lnx-division-001',wake_id:'W1',mission_id:'M-001',action_type:'TEST',briefing:'hello',created_at:'2026-08-31T00:00:00Z',evidence_refs:[]}},'die-lnx-division-001');
const a=updateThreadState(null,{{principalId:'die-lnx-division-001',conversationUrl:t.conversationUrl,conversationId:t.conversationId,at:'2026-08-31T00:00:00Z'}});
const b=updateThreadState(a,{{principalId:'die-lnx-division-001',conversationUrl:'https://chatgpt.com/c/def-456',conversationId:'def-456',at:'2026-08-31T00:01:00Z'}});
console.log(JSON.stringify({{t,env,b}}));'''
    out = subprocess.run(["node", "--input-type=module", "-e", source], text=True, capture_output=True, check=False)
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert data["t"]["conversationId"] == "abc-123"
    assert data["b"]["generation"] == 2
    assert data["b"]["history"][0]["lifecycle_state"] == "superseded"


def test_document_explicitly_blocks_autonomous_submission_claim() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "MUST NOT port" in text
    assert "press Send" in text
    assert "future supported provider actuator" in text
    assert "exactly_one_active_thread" in text
