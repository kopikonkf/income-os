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
      '<svg viewBox="0 0 10 10">prose<path d="M0 0 L1 1"/></svg>',
    ]
    for x in bad:
      with pytest.raises(m.NativeSvgPipelineError):m.validate_and_normalize(x)

def test_curves_are_supported_while_unsupported_commands_and_unsafe_geometry_fail_closed():
    cases=[
      ('<svg viewBox="0 0 100 100"><path d="M0 0 R10 10"/></svg>','PATH_COMMAND_UNSUPPORTED'),
      ('<svg viewBox="0 0 100 100"><path d="M0 0 L200 1"/></svg>','PATH_OUT_OF_BOUNDS'),
      ('<svg viewBox="0 0 100 100"><path d="M0 0 L1 1" font-family="Arial"/></svg>','SVG_EXTERNAL_OR_STYLE_FORBIDDEN'),
    ]
    for x,code in cases:
      with pytest.raises(m.NativeSvgPipelineError) as e:m.validate_and_normalize(x)
      assert e.value.code==code
    many='<svg viewBox="0 0 100 100">'+''.join('<path d="M0 0 L1 1"/>' for _ in range(4))+'</svg>'
    with pytest.raises(m.NativeSvgPipelineError,match='PATH_COUNT_EXCEEDED'):m.validate_and_normalize(many,max_paths=3)

def test_cubic_quadratic_smooth_and_arc_curves_render_and_remain_editable():
    samples=[
      '<svg viewBox="0 0 100 100"><path d="M20 50 C20 20 80 20 80 50 S70 80 50 80 Q30 80 20 50 Z" fill="#336699"/></svg>',
      '<svg viewBox="0 0 100 100"><path d="M20 50 Q50 10 80 50 T20 50 Z" fill="#336699"/></svg>',
      '<svg viewBox="0 0 100 100"><path d="M20 50 A30 30 0 1 1 80 50 A30 30 0 1 1 20 50 Z" fill="#336699"/></svg>',
    ]
    for svg in samples:
      normalized=m.validate_and_normalize(svg)
      assert normalized['native_editable'] is True
      assert normalized['total_points'] > 4
      assert normalized['render_ink_pixels_512'] > 16
      assert '<path' in normalized['canonical_svg']

def test_safe_shapes_are_supported_with_inherited_flat_style():
    svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <g fill="#336699" stroke="none">
        <rect x="5" y="5" width="20" height="20" rx="4"/>
        <circle cx="45" cy="15" r="10"/>
        <ellipse cx="75" cy="15" rx="12" ry="8"/>
        <polygon points="5,40 25,40 15,60"/>
        <polyline points="35,40 45,60 55,40"/>
      </g>
      <line x1="65" y1="45" x2="95" y2="65" fill="none" stroke="#000000" stroke-width="2"/>
    </svg>'''
    normalized=m.validate_and_normalize(svg)
    assert normalized['path_count']==0
    assert normalized['geometry_count']==6
    assert normalized['shape_count']==6
    assert {element['kind'] for element in normalized['shapes']} == {'rect','circle','ellipse','polygon','polyline','line'}
    assert all(tag in normalized['canonical_svg'] for tag in ('<rect','<circle','<ellipse','<polygon','<polyline','<line'))
    assert normalized['render_ink_pixels_512'] > 16
    assert b'setrgbcolor' in m.eps_bytes(normalized)

def test_render_and_geometry_bounds_are_explicitly_capped():
    normalized=m.validate_and_normalize('<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="20" fill="#000000"/></svg>')
    with pytest.raises(m.NativeSvgPipelineError,match='RENDER_SIZE_INVALID'):
      m.render_png_image(normalized,size=4097)
    with pytest.raises(m.NativeSvgPipelineError,match='PATH_COMPLEXITY_EXCEEDED'):
      m.validate_and_normalize('<svg viewBox="0 0 100 100"><path d="M20 50 C20 20 80 20 80 50"/></svg>',max_total_points=8)

def test_blank_invisible_and_doctype_are_rejected():
    with pytest.raises(m.NativeSvgPipelineError,match='INVISIBLE_PATH'):
      m.validate_and_normalize('<svg viewBox="0 0 100 100"><path d="M0 0 L1 1" fill="none" stroke="none"/></svg>')
    with pytest.raises(m.NativeSvgPipelineError,match='SVG_DTD_FORBIDDEN'):
      m.validate_and_normalize('<!DOCTYPE svg><svg viewBox="0 0 10 10"><path d="M0 0 L1 1"/></svg>')
