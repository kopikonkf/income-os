import base64,importlib.util,json,sys
from pathlib import Path
import jsonschema,pytest
R=Path(__file__).resolve().parents[3];P=R/'company/factory-asset/providers/qwen/adapter.py';s=importlib.util.spec_from_file_location('fa111q',P);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);SC=json.loads((R/'company/factory-asset/schemas/image-provider.schema.json').read_text())

def test_capability_and_transport_order():
 c=m.capability();jsonschema.validate(c,SC);assert c['transport_classes']==['SESSION_API','BROWSER_CDP'];assert c['capacity_state']=='UNKNOWN';assert m.select_transport()=='SESSION_API';assert m.select_transport('browser_cdp')=='BROWSER_CDP'

def test_invalid_transport_fails_closed():
 with pytest.raises(m.QwenAdapterError) as e:m.select_transport('AUTO_MAGIC')
 assert e.value.code=='TRANSPORT_UNSUPPORTED'

def test_new_chat_parse_and_t2i_payload():
 assert m.parse_chat_id({'data':{'id':'chat-123'}})=='chat-123'
 ctx=m.SessionRequestContext(chat_id='chat-123',parent_id=None,fid='fid-1',child_id='child-1',timestamp=1770000000,prompt='pink square')
 p=m.build_t2i_payload(ctx);msg=p['messages'][0];assert p['model']=='qwen3.8-max' and msg['chat_type']=='t2i' and msg['sub_chat_type']=='t2i';assert msg['content']=='pink square';assert msg['feature_config']['image_enabled'] is True

def test_sse_collects_content_tools_and_parent():
 lines=['data: '+json.dumps({'choices':[{'delta':{'content':'https://cdn.qwenlm.ai/output/a.png?key=x','extra':{'tool_result':[{'image':'https://cdn.qwenlm.ai/output/b.png?key=y'}]}} ,'message_id':'m1'}]}),'data: [DONE]']
 r=m.parse_sse(lines);assert 'a.png' in r['text'];assert r['extra_image_urls']==['https://cdn.qwenlm.ai/output/b.png?key=y'];assert r['parent_id']=='m1'

def test_candidate_parser_handles_direct_markdown_json_and_base64():
 direct=m.extract_image_candidates(text='https://x.test/a.png?z=1');assert direct['urls']==['https://x.test/a.png?z=1']
 md=m.extract_image_candidates(text='![x](https://x.test/a.jpg)');assert 'https://x.test/a.jpg' in md['urls']
 js=m.extract_image_candidates(text=json.dumps({'image_url':'https://x.test/b.webp'}));assert 'https://x.test/b.webp' in js['urls']
 raw=b'\x89PNG'+b'x'*1600;b64=base64.b64encode(raw).decode();b=m.extract_image_candidates(text=b64);assert b['b64']==[b64]

def test_qwen_preview_transform_removed_signed_key_preserved():
 src='https://cdn.qwenlm.ai/output/u/image_gen/j/id.png?key=abc123&x-oss-process=image/resize,m_mfit,w_450,h_450';o=m.provider_original_url(src);assert 'key=abc123' in o and 'x-oss-process' not in o
 assert m.provider_original_url('https://example.test/a.png?x-oss-process=preview').endswith('x-oss-process=preview')

def test_http_failure_is_typed():
 assert m.classify_http_failure(status=401)['code']=='AUTH_REQUIRED';assert m.classify_http_failure(status=429)=={'code':'RATE_LIMITED','retryable':True};assert m.classify_http_failure(status=503)['retryable'] is True;assert m.classify_http_failure(status=400,body_text='captcha')['code']=='PROTECTION_CHALLENGE'

def test_browser_fallback_delegates_ownership_to_muxia():
 e=m.browser_fallback_envelope(prompt='pink square',deadline_seconds=300);assert e['browser_runtime_owner']=='MUXIA';assert e['primary_transport']=='SESSION_API';assert e['credential_values_embedded'] is False and e['session_material_embedded'] is False

def test_extraction_has_no_windows_secret_or_browser_owner_debt():
 text=P.read_text();forbidden=('D:/ASSETS','C:\\','load_credential','credentials/qwen','playwright','connect_over_cdp','Cookie":','cookie =','token =')
 for x in forbidden: assert x not in text
 prov=json.loads((P.parent/'source-provenance.json').read_text());assert prov['extraction_policy']['copied_credentials'] is False;assert prov['extraction_policy']['copied_browser_ownership'] is False
