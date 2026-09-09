from pathlib import Path
R=Path(__file__).resolve().parents[3]
WORKER=R/'company/factory-asset/lib/console_broker_provider_worker.mjs'
INDEX=R/'company/factory-asset/lib/provider_leased_strategies.mjs'
MODULES=[R/'company/factory-asset/providers/chatgpt/linux/chatgpt_leased_strategy.mjs',R/'company/factory-asset/providers/gemini/linux/gemini_leased_strategy.mjs',R/'company/factory-asset/providers/manus/linux/manus_leased_strategy.mjs',R/'company/factory-asset/providers/duckai/linux/duckai_leased_strategy.mjs']
def test_worker_supports_five_leased_browser_providers():
 t=WORKER.read_text().lower()
 for p in ('qwen','chatgpt','gemini','manus','duckai'): assert f"'{p}'" in t
 assert 'providerSettleMs'.lower() in t.lower() and 'prepareLeasedStrategy'.lower() in t.lower()
def test_provider_strategies_do_not_launch_second_browser_or_read_secrets():
 t='\n'.join(p.read_text().lower() for p in MODULES+[INDEX])
 for bad in ('launchpersistentcontext','--user-data-dir','playwrightchromiumdriver','context.cookies','storagestate','document.cookie','localstorage','sessionstorage'): assert bad not in t
def test_manus_hydration_wait_and_proven_extractors_are_preserved():
 c=MODULES[0].read_text();g=MODULES[1].read_text();m=MODULES[2].read_text();d=MODULES[3].read_text()
 assert 'settleMs = 12000' in m and 'manuscdn.com' in m and 'files.manuscdn.com' in m
 assert 'oaiusercontent.com' in c and '/backend-api/estuary/content' in c and 'provider_image_url_browser_context' in c
 assert 'provider_generated_image_response_body_after_dispatch' in g and 'downloadSelector' in g and 'fresh-generated-dom-after-download-control' in g
 assert 'Create Image' in d and 'provider_image_response_body' in d and 'provider_data_uri_dom' in d
 assert 'savedAIChatData' in d and 'chat-images' in d and 'duckai_indexeddb_chat_images_blob' in d
 assert 'legacy418Seen' in d and 'challengeAssetSeen' in d and 'E_HUMAN_CHALLENGE_REQUIRED' in d and 'E_DUCK_SCOPED_418_NO_IMAGE_TIMEOUT' in d and 'state.challenge=' not in d
