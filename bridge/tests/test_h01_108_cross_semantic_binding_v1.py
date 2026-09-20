from pathlib import Path
import importlib.util
import json

R=Path(__file__).resolve().parents[2]
H=R/'company/company-os/die-h01/engineering'

def load_capture():
    p=H/'h01_108_capture.py'
    spec=importlib.util.spec_from_file_location('h01_108_capture_guard',p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_cross_semantic_hash_reuse_is_rejected(tmp_path):
    mod=load_capture()
    prior=tmp_path/'001-book-gemini-a1'
    prior.mkdir()
    digest='a'*64
    (prior/'artifact-created.receipt.json').write_text(json.dumps({
        'provider_original_sha256':digest,
        'semantic_asset_id':'H01SVG-CAND-BOOK'
    }))
    current=tmp_path/'002-butterfly-gemini-a1'
    current.mkdir()
    try:
        mod.assert_unique_semantic_hash(tmp_path,digest,'H01SVG-CAND-BUTTERFLY',current)
    except RuntimeError as e:
        assert 'E_CROSS_SEMANTIC_HASH_REUSE' in str(e)
    else:
        raise AssertionError('cross-semantic hash reuse must fail closed')

def test_same_semantic_hash_replay_is_allowed(tmp_path):
    mod=load_capture()
    prior=tmp_path/'001-book-gemini-a1'
    prior.mkdir()
    digest='b'*64
    (prior/'artifact-created.receipt.json').write_text(json.dumps({
        'provider_original_sha256':digest,
        'semantic_asset_id':'H01SVG-CAND-BOOK'
    }))
    current=tmp_path/'001-book-gemini-a2'
    current.mkdir()
    mod.assert_unique_semantic_hash(tmp_path,digest,'H01SVG-CAND-BOOK',current)

def test_gemini_download_controls_are_post_baseline_only():
    s=(H/'provider_svg_playwright_strategy.mjs').read_text()
    assert 'markBaselineSvgDownloadControls' in s
    assert "data-die-baseline-svg-download" in s
    assert 'freshSvgDownloadControls' in s
    assert "if(controls.length>0)" in s
