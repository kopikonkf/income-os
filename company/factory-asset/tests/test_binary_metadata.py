import importlib.util,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('bm',R/'company/factory-asset/lib/binary_metadata.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m)
SRC=R/'company/factory-asset/fixtures/provider-original-v1/opaque.jpg'
META={'title':'Headphones - Photo','description':'Headphones created for audio technology concepts.','keywords':['headphones','audio','technology','concepts','photo'],'ai_disclosure':'GENERATIVE_AI'}
def test_jpeg_injection_roundtrip_preserves_source_and_pixels(tmp_path):
 out=tmp_path/'listing.jpg';before=m.sha256_file(SRC);r=m.inject_jpeg(source_path=SRC,output_path=out,metadata=META);assert r['result']=='PASS';assert r['source_sha256']==before and m.sha256_file(SRC)==before;assert r['output_sha256']!=before;assert r['dimensions']==[12,8];rb=m.readback_jpeg(out);assert rb['xmp']==META and rb['iptc']==META
def test_same_file_overwrite_forbidden():
 with pytest.raises(m.BinaryMetadataError) as e:m.inject_jpeg(source_path=SRC,output_path=SRC,metadata=META)
 assert e.value.code=='IMMUTABLE_SOURCE_OVERWRITE_FORBIDDEN'
def test_existing_managed_metadata_rejected(tmp_path):
 first=tmp_path/'first.jpg';second=tmp_path/'second.jpg';m.inject_jpeg(source_path=SRC,output_path=first,metadata=META)
 with pytest.raises(m.BinaryMetadataError) as e:m.inject_jpeg(source_path=first,output_path=second,metadata=META)
 assert e.value.code in {'EXISTING_XMP_UNSUPPORTED','EXISTING_IPTC_UNSUPPORTED'}
def test_corrupt_jpeg_rejected(tmp_path):
 bad=tmp_path/'bad.jpg';bad.write_bytes(b'\xff\xd8\xff\xe1\x00')
 with pytest.raises(m.BinaryMetadataError):m.inject_jpeg(source_path=bad,output_path=tmp_path/'x.jpg',metadata=META)
def test_unsupported_webp_is_sidecar_only_and_unchanged(tmp_path):
 src=R/'company/factory-asset/fixtures/provider-original-v1/opaque.png';before=m.sha256_file(src);r=m.inject_or_sidecar(source_path=src,output_path=tmp_path/'x.png',format='PNG',metadata=META);assert r['result']=='SIDECAR_ONLY';assert r['output_path'] is None and m.sha256_file(src)==before
def test_readback_detects_tampered_xmp(tmp_path):
 out=tmp_path/'listing.jpg';m.inject_jpeg(source_path=SRC,output_path=out,metadata=META);data=out.read_bytes().replace(b'Headphones - Photo',b'Headphones - Faux ',1);tam=tmp_path/'tam.jpg';tam.write_bytes(data)
 rb=m.readback_jpeg(tam);assert rb['xmp']['title']!='Headphones - Photo'
