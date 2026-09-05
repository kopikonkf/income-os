from pathlib import Path
import importlib.util
R=Path(__file__).resolve().parents[3]; A=R/'company/factory-asset/providers/manus/adapter.py'; C=R/'company/factory-asset/providers/manus/linux/manus_muxia_canary.mjs'
def load():
 s=importlib.util.spec_from_file_location('m',A);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_contract():
 m=load(); c=m.capability(); assert c['provider_id']=='manus' and c['transport_classes']==['BROWSER_CDP'] and c['browser_runtime_owner']=='MUXIA' and c['profile_id']=='chatgpt-linux-a'
def test_only_proven_route():
 s=load().browser_strategy(); assert s['acquisition_route']=='GENERATED_MANUSCDN_RESPONSE_BODY'; assert s['guessed_api_endpoints'] is False; assert 'files.manuscdn.com' in s['generated_host_rule']
def test_no_stale_api_or_secrets():
 s=A.read_text().lower();
 for bad in ('/api/task','callapiservice','authorization: bearer','cookie=','token=','credentials/manus','d:/oauth','d:/assets'): assert bad not in s
def test_canary_single_bounded_dispatch():
 s=C.read_text(); assert s.count("editor.press('Enter')")==1; assert 'Date.now()+300000' in s; assert "host==='files.manuscdn.com'" in s
def test_canary_secret_boundary():
 s=C.read_text().lower(); assert 'context.cookies' not in s and 'storagestate' not in s and 'credential_values_read:false' in s and 'cookies_or_tokens_read:false' in s and 'operator_actions_after_dispatch:0' in s