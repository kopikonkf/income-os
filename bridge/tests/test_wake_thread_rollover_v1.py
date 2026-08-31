from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "company" / "browser" / "linux" / "wake_transport_core.mjs"
DOC = ROOT / "docs" / "architecture" / "DIE_LINUX_SAFE_WAKE_TRANSPORT_V1.md"


def test_rollover_selector_chooses_newest_thread_different_from_active() -> None:
    source = (
        f"import {{selectNewestUnboundThread}} from {json.dumps(CORE.as_uri())}; "
        "console.log(JSON.stringify(selectNewestUnboundThread(["
        "'https://chatgpt.com/c/old','https://chatgpt.com/','https://chatgpt.com/c/new-1','https://chatgpt.com/c/new-2'"
        "],'old')));"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", source], text=True, capture_output=True, check=False)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["conversationId"] == "new-2"


def test_rollover_is_operator_send_only_and_preserves_existing_thread_until_bind() -> None:
    text = CORE.read_text(encoding="utf-8")
    assert "prepare-rotation" in text and "bind-newest" in text
    assert "awaiting_operator_send_and_rebind" in text
    assert "submitted_by_transport: false" in text
    assert "submitted: false" in text
    assert "context.newPage()" in text
    assert "from_generation" in text and "to_generation" in text
    assert "keyboard.press" not in text and ".click()" not in text


def test_rollover_document_uses_context_snapshot_not_transcript_copy() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "prepare-rotation" in text
    assert "bind-newest" in text
    assert "generation `N+1`" in text
    assert "context_snapshot" in text
    assert "transcript copying is neither required nor authoritative" in text
