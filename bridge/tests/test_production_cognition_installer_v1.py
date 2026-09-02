from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_installer_is_no_agent_minute_cognition_line():
 t=(ROOT/'company/die-agents/hermes/linux/install-production-cognition-v1.sh').read_text()
 assert 'die-production-cognition-v1' in t
 assert "SCHEDULE='*/1 * * * *'" in t
 assert '--no-agent' in t and '--deliver telegram' in t
 assert 'production-cognition/production_cognition_tick.sh' in t
 assert 'exec /usr/bin/python3' in t
 assert 'import jsonschema' in t
 assert 'cognition-receipts' in t
 assert 'die-hermes' in t and 'die-runtime' in t
def test_authority_doc_preserves_irreversible_boundaries():
 t=(ROOT/'company/die-agents/hermes/linux/PRINCIPAL_SOCIETY_AUTHORITY_V1.md').read_text()
 assert 'reversible internal cognition transport' in t
 assert 'does **not** authorize account/profile configuration' in t
 assert 'marketplace submission/publication' in t
