import importlib.util
import json
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company/factory-asset/lib/console_asset_operations.py"
CONSOLE = ROOT / "company/factory-asset/console-prototype"


def load_module():
    spec = importlib.util.spec_from_file_location("console_asset_ops_test", LIB)
    mod = importlib.util.module_from_spec(spec); assert spec and spec.loader
    sys.modules[spec.name] = mod; spec.loader.exec_module(mod); return mod


def load_server():
    spec = importlib.util.spec_from_file_location("console_asset_ops_server_test", CONSOLE / "server.py")
    mod = importlib.util.module_from_spec(spec); assert spec and spec.loader
    sys.modules[spec.name] = mod; spec.loader.exec_module(mod); return mod


def walk_keys(v):
    if isinstance(v, dict):
        for k, child in v.items():
            yield str(k).lower(); yield from walk_keys(child)
    elif isinstance(v, list):
        for child in v: yield from walk_keys(child)


def test_c017_trace_binds_original_master_derivatives_metadata_rights_package_and_founder_qc():
    d = load_module().build_asset_operations(ROOT)
    assert d["mode"] == "READ_ONLY_CANONICAL_TRACE" and d["asset_count"] == 1 and d["derivative_count"] == 3
    a = d["assets"][0]
    assert a["canonical_truth"] is True
    assert len(a["provider_original"]["sha256"]) == 64 and a["provider_original"]["immutable"] is True
    assert len(a["master"]["sha256"]) == 64 and a["master"]["technical_qa"] == "PASS"
    assert all(x["qa_state"] == "PASS" and x["compatibility_state"] == "COMPATIBLE" and len(x["sha256"]) == 64 for x in a["derivatives"])
    assert a["metadata"]["iptc_readback"] == "PASS" and a["metadata"]["xmp_readback"] == "PASS"
    assert a["qa_rights"]["automated_rights_signal"] == "PASS" and a["qa_rights"]["human_rights_clearance"] is False
    assert a["qa_rights"]["founder_qc_decision"] == "APPROVE"
    assert a["package"]["state"] == "PACKAGE_READY" and a["package"]["blockers"] == []


def test_content_hash_index_resolves_every_exact_hash_to_same_semantic_asset():
    d = load_module().build_asset_operations(ROOT); a=d["assets"][0]
    idx={(x["role"],x["sha256"]):x["semantic_asset_id"] for x in d["content_hash_index"]}
    assert len(idx) == len(a["exact_hashes"])
    for role,sha in a["exact_hashes"].items(): assert idx[(role,sha)] == a["semantic_asset_id"]


def test_asset_operations_has_zero_external_authority_and_no_private_paths_or_secret_keys():
    d = load_module().build_asset_operations(ROOT); a=d["assets"][0]
    assert a["authority"] == {"submission_authorized":False,"publication_authorized":False,"marketplace_upload":False,"provider_calls_performed":False,"spend_usd":0}
    text=json.dumps(d).lower(); assert "/var/lib/" not in text and "d:\\\\factory_asset" not in text
    forbidden={"cookie","cookies","token","password","credential","profile_dir","debug_port","control_port","lease_id","claim_url","private_key"}
    assert not (set(walk_keys(d)) & forbidden)


def test_asset_operations_http_roundtrip_and_ui_hash_search():
    m=load_server(); httpd=m.ThreadingHTTPServer(("127.0.0.1",0),m.Handler); t=threading.Thread(target=httpd.serve_forever,daemon=True); t.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_port}/api/assets",timeout=5) as r: d=json.loads(r.read())
        assert d["schema"] == "die.factory-asset.console-asset-operations.v1" and d["assets"][0]["package"]["state"] == "PACKAGE_READY"
    finally: httpd.shutdown(); httpd.server_close(); t.join(timeout=5)
    js=(CONSOLE/"app.js").read_text(encoding="utf-8"); html=(CONSOLE/"index.html").read_text(encoding="utf-8")
    assert "getLocal('/api/assets')" in js and "Semantic asset ID or exact content SHA-256" in js
    for marker in ("Derivatives + QA","Metadata + binary readback","Rights / package / lineage","Founder QC"):
        assert marker in js
    assert 'data-view="assets"' in html and 'data-view-panel="assets"' in html
