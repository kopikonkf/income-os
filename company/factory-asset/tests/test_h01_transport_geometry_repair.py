import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from native_svg_pipeline import validate_and_normalize as norm

def wrap(s):return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'+s+'</svg>'
def test_straight_dashes_equal_explicit_geometry():
 raw=wrap('<path d="M10,20 L30,20" fill="none" stroke="#000000" stroke-width="4" stroke-dasharray="6,6"/>')
 with pytest.raises(ValueError):norm(raw)
 expected=wrap('<path d="M10 20 L16 20" fill="none" stroke="#000000" stroke-width="4"/><path d="M22 20 L28 20" fill="none" stroke="#000000" stroke-width="4"/>')
 assert norm(raw,repair_transport_geometry=True)['canonical_svg']==norm(expected)['canonical_svg']
def test_invisible_geometry_does_not_change_visible_master():
 shape='<rect x="20" y="20" width="60" height="60" fill="#334455"/>'
 raw=wrap(shape+'<ellipse cx="50" cy="50" rx="20" ry="10" fill="none"/>')
 with pytest.raises(ValueError):norm(raw)
 assert norm(raw,repair_transport_geometry=True)['canonical_svg']==norm(wrap(shape))['canonical_svg']
def test_only_nonrendering_ui_label_is_removed():
 shape='<rect x="20" y="20" width="60" height="60" fill="#334455"/>'
 assert norm(wrap(shape+'Plain Text'),repair_transport_geometry=True)['canonical_svg']==norm(wrap(shape))['canonical_svg']
 with pytest.raises(ValueError):norm(wrap(shape+'Brand Name'),repair_transport_geometry=True)
@pytest.mark.parametrize('body',[
 '<path d="M10 10 C20 20 30 20 40 10" stroke-dasharray="6 6"/>',
 '<path d="M10 10 L40 10" stroke-dasharray="0 0"/>',
 '<path d="M10 10 L40 10" stroke-dasharray="6 6"><script/></path>',
 '<ellipse cx="50" cy="50" rx="20" ry="10" fill="none"/>',
 '<text>Plain Text</text>',
])
def test_repair_does_not_bypass_safety_or_accept_blank(body):
 with pytest.raises(ValueError):norm(wrap(body),repair_transport_geometry=True)
