from pathlib import Path
import re

R = Path(__file__).resolve().parents[2]
N = R / 'company/company-os/die-h01/engineering/nexaburst'


def test_nexaburst_kw_psr_sources_are_preserved_without_embedded_credentials():
    files = [
        N / 'nexaburst-kw-enrich.py',
        N / 'nexaburst-v2-worker-psr.py',
        N / 'nexaburst-psr-postprod-watchdog.sh',
    ]
    for path in files:
        assert path.is_file()
        text = path.read_text(encoding='utf-8')
        assert not re.search(
            r'(?i)\b(?:token|secret|password|api_key|private_key)\s*=\s*["\'][^"\']+["\']',
            text,
        )


def test_kw_enrichment_emits_title_description_and_keyword_receipts():
    src = (N / 'nexaburst-kw-enrich.py').read_text(encoding='utf-8')
    assert 'EXACTLY 50' in src
    assert "'title': title" in src
    assert "'description': desc" in src
    assert "'keywords': kw" in src
    assert "receipts.jsonl" in src


def test_psr_worker_threads_kw_receipt_into_factory_metadata_overrides():
    src = (N / 'nexaburst-v2-worker-psr.py').read_text(encoding='utf-8')
    assert "KW_RECEIPTS=Path('/var/lib/die/h01/nexaburst-kw-psr/receipts.jsonl')" in src
    assert "ov['title_override']=o['title']" in src
    assert "ov['description_override']=o['description']" in src
    assert "ov['keywords_override']=o['keywords']" in src
    assert "kwargs['metadata_overrides']=ov" in src
    assert 'postprocess_raster_workspace(**kwargs)' in src


def test_psr_worker_keeps_legacy_fallback_for_missing_receipt():
    src = (N / 'nexaburst-v2-worker-psr.py').read_text(encoding='utf-8')
    assert "if ov: kwargs['metadata_overrides']=ov" in src
    assert "Assets without a KW receipt fall back to legacy minimal metadata." in src
