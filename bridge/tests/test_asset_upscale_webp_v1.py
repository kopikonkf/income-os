from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'bridge/income_os_bridge/asset_upscale.py'
spec=importlib.util.spec_from_file_location('upscale_webp_test',P); UP=importlib.util.module_from_spec(spec); spec.loader.exec_module(UP)


def make_webp_header(path: Path, width: int, height: int, kind: str) -> None:
    if kind == 'VP8X':
        payload=b'\x00\x00\x00\x00'+(width-1).to_bytes(3,'little')+(height-1).to_bytes(3,'little')
        chunk=b'VP8X'+len(payload).to_bytes(4,'little')+payload
    elif kind == 'VP8L':
        w=width-1; h=height-1
        packed=bytes([w&0xff,((w>>8)&0x3f)|((h&0x3)<<6),(h>>2)&0xff,(h>>10)&0x0f])
        payload=b'\x2f'+packed
        chunk=b'VP8L'+len(payload).to_bytes(4,'little')+payload
    elif kind == 'VP8 ':
        payload=b'\x00\x00\x00\x9d\x01\x2a'+(width&0x3fff).to_bytes(2,'little')+(height&0x3fff).to_bytes(2,'little')
        chunk=b'VP8 '+len(payload).to_bytes(4,'little')+payload
    else:
        raise AssertionError(kind)
    path.write_bytes(b'RIFF'+(4+len(chunk)).to_bytes(4,'little')+b'WEBP'+chunk)


def test_webp_dimension_detection_supports_vp8_vp8l_vp8x(tmp_path: Path) -> None:
    for kind,dims in [('VP8X',(1024,768)),('VP8L',(513,257)),('VP8 ',(640,480))]:
        p=tmp_path/f'{kind.strip()}.webp'; make_webp_header(p,*dims,kind)
        assert UP.image_dimensions(p)==(*dims,'WEBP')
