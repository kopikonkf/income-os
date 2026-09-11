import importlib.util,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('nsp',ROOT/'company/factory-asset/lib/native_svg_pipeline.py');m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m)
GOOD='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M 10 20 L 90 20 L 80 90 L 20 90 Z" fill="#336699" stroke="#000000" stroke-width="2"/></svg>'
OUTLINE='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M 10 20 L 90 20 L 80 90 L 20 90 Z" fill="none" stroke="#000000" stroke-width="4"/></svg>'

def test_safe_svg_is_editable_independently_rendered_and_deterministic():
    a=m.package_svg_master(svg_text=GOOD,semantic_asset_id='FASA-TEST_ICON',blueprint_sha256='a'*64,provider_prompt_sha256='b'*64)
    b=m.package_svg_master(svg_text=GOOD,semantic_asset_id='FASA-TEST_ICON',blueprint_sha256='a'*64,provider_prompt_sha256='b'*64)
    assert a['package']==b['package']
    assert a['bytes']==b['bytes']
    assert a['package']['master']['format']=='SVG' and a['package']['master']['native_editable'] is True
    assert a['package']['master']['conversion_from_raster'] is False
    assert a['package']['qa']['independent_render']=='PIL_FROM_PARSED_VECTOR_GEOMETRY'
    assert a['package']['qa']['render_ink_pixels_512']>16
    assert {x['format'] for x in a['package']['derivatives']}=={'EPS','PNG','JPEG'}
    assert all(x['semantic_identity_effect']=='NONE' for x in a['package']['derivatives'])
    assert a['package']['semantic_asset_count']==1 and a['package']['derivatives_create_new_semantic_asset'] is False

def test_outline_path_renders_and_packages_without_fill():
    r=m.package_svg_master(svg_text=OUTLINE,semantic_asset_id='FASA-TEST_OUTLINE',blueprint_sha256='a'*64,provider_prompt_sha256='b'*64)
    assert r['package']['qa']['render_ink_pixels_512']>16
    assert b'setlinewidth' in r['bytes']['EPS']

def test_script_external_embedded_raster_text_and_style_are_rejected():
    bad=[
      '<svg viewBox="0 0 10 10"><script>alert(1)</script><path d="M0 0 L1 1"/></svg>',
      '<svg viewBox="0 0 10 10"><image href="data:image/png;base64,xx"/><path d="M0 0 L1 1"/></svg>',
      '<svg viewBox="0 0 10 10"><text>brand</text><path d="M0 0 L1 1"/></svg>',
      '<svg viewBox="0 0 10 10"><path d="M0 0 L1 1" style="fill:url(http://x)"/></svg>',
      '<svg viewBox="0 0 10 10"><use href="https://x/y.svg#z"/></svg>',
    ]
    for x in bad:
      with pytest.raises(m.NativeSvgPipelineError):m.validate_and_normalize(x)

def test_unsupported_curves_fonts_out_of_bounds_and_complexity_fail_closed():
    cases=[
      ('<svg viewBox="0 0 100 100"><path d="M0 0 C10 10 20 20 30 30"/></svg>','PATH_COMMAND_UNSUPPORTED'),
      ('<svg viewBox="0 0 100 100"><path d="M0 0 L200 1"/></svg>','PATH_OUT_OF_BOUNDS'),
      ('<svg viewBox="0 0 100 100"><path d="M0 0 L1 1" font-family="Arial"/></svg>','SVG_EXTERNAL_OR_STYLE_FORBIDDEN'),
    ]
    for x,code in cases:
      with pytest.raises(m.NativeSvgPipelineError) as e:m.validate_and_normalize(x)
      assert e.value.code==code
    many='<svg viewBox="0 0 100 100">'+''.join('<path d="M0 0 L1 1"/>' for _ in range(4))+'</svg>'
    with pytest.raises(m.NativeSvgPipelineError,match='PATH_COUNT_EXCEEDED'):m.validate_and_normalize(many,max_paths=3)

def test_blank_invisible_and_doctype_are_rejected():
    with pytest.raises(m.NativeSvgPipelineError,match='INVISIBLE_PATH'):
      m.validate_and_normalize('<svg viewBox="0 0 100 100"><path d="M0 0 L1 1" fill="none" stroke="none"/></svg>')
    with pytest.raises(m.NativeSvgPipelineError,match='SVG_DTD_FORBIDDEN'):
      m.validate_and_normalize('<!DOCTYPE svg><svg viewBox="0 0 10 10"><path d="M0 0 L1 1"/></svg>')
