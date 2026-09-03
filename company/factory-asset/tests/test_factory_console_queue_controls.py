import importlib.util
import json
import sys
import threading
import urllib.request
from pathlib import Path

import jsonschema
import pytest

ROOT=Path(__file__).resolve().parents[3]
CONSOLE=ROOT/'company/factory-asset/console-prototype'
SCHEMA=json.loads((ROOT/'company/factory-asset/schemas/factory-console-api.schema.json').read_text())
VALIDATOR=jsonschema.Draft202012Validator(SCHEMA)

def load_server():
 spec=importlib.util.spec_from_file_location('console_c006_server',CONSOLE/'server.py');m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

@pytest.fixture()
def server():
 m=load_server();m.CORE_QUEUE=m.factory_queue.FactoryJobQueue();m._seed_queue();return m

def command(job,action,n='001'):
 return {'schema':'die.factory-asset.console-api.v1','kind':'CONTROL_COMMAND','command_id':f'command-{n}-{action.lower()}','job_id':job,'action':action}

def test_seeded_console_queue_is_real_core_state(server):
 state=server.queue_state();assert state['provider_dispatch_performed'] is False
 states={e['state'] for e in state['events']};assert {'READY','RUNNING','PAUSED','RETRY_WAIT'}<=states
 for e in state['events']:VALIDATOR.validate(e)

def test_start_pause_resume_cancel_use_factory_core(server):
 assert server.apply_queue_command(command('FCJOB-DEMO-READY','START'))['event']['state']=='RUNNING'
 assert server.apply_queue_command(command('FCJOB-DEMO-READY','PAUSE','002'))['event']['state']=='PAUSED'
 assert server.apply_queue_command(command('FCJOB-DEMO-READY','RESUME','003'))['event']['state']=='READY'
 assert server.apply_queue_command(command('FCJOB-DEMO-READY','START','004'))['event']['state']=='RUNNING'
 result=server.apply_queue_command(command('FCJOB-DEMO-READY','CANCEL','005'));assert result['event']['state']=='CANCELLED';assert result['provider_dispatch_performed'] is False

def test_retry_control_obeys_core_retry_counter(server):
 event=server.apply_queue_command(command('FCJOB-DEMO-RETRY','RETRY'))['event'];assert event['state']=='READY';assert event['retries']==1

def test_batch_enqueue_is_idempotent_and_does_not_dispatch(server):
 bp=json.loads((ROOT/'company/factory-asset/fixtures/shopping-bag-blueprint-v2/photo.json').read_text())
 preview=server.compile_blueprint_payload({'blueprint':bp,'ui_constraints':{}})
 batch=server.create_batch_intent({'compile_preview':preview,'quantity':3,'label':'queue batch','ui_constraints':{}})
 before=len(server.CORE_QUEUE.list());one=server.submit_batch_to_queue({'batch_intent':batch});mid=len(server.CORE_QUEUE.list());two=server.submit_batch_to_queue({'batch_intent':batch});after=len(server.CORE_QUEUE.list())
 assert one['created_or_reused']==3 and two['created_or_reused']==3;assert mid==before+3;assert after==mid;assert one['provider_dispatch_performed'] is False

def test_control_envelope_rejects_provider_or_browser_fields(server):
 x=command('FCJOB-DEMO-READY','START');x['provider_endpoint']='https://example.invalid'
 with pytest.raises(server.ConsoleRequestError) as e:server.apply_queue_command(x)
 assert e.value.code=='INVALID_CONTROL_COMMAND'

def test_http_queue_read_and_control_roundtrip(server):
 httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}/api/queue/jobs',timeout=5) as response:state=json.loads(response.read())
  assert state['events'] and state['provider_dispatch_performed'] is False
  body=json.dumps(command('FCJOB-DEMO-READY','START','http')).encode();req=urllib.request.Request(f'http://127.0.0.1:{httpd.server_port}/api/queue/action',data=body,headers={'Content-Type':'application/json'},method='POST')
  with urllib.request.urlopen(req,timeout=5) as response:result=json.loads(response.read())
  assert result['event']['state']=='RUNNING';assert result['provider_dispatch_performed'] is False
 finally:httpd.shutdown();httpd.server_close();thread.join(timeout=5)

def test_console_ui_exposes_all_governed_controls_and_core_state_fields():
 js=(CONSOLE/'app.js').read_text()
 for marker in ("'/api/queue/jobs'","'/api/queue/action'","'/api/queue/submit'",'START','PAUSE','RESUME','CANCEL','RETRY','recovery_count','retries}/2','Provider Dispatch Locked'):
  assert marker in js
 for forbidden in ('cdp_url','browser_profile','session_token','rpc_id'):
  assert forbidden not in js

def test_console_server_has_no_provider_dispatch_implementation():
 src=(CONSOLE/'server.py').read_text().lower()
 assert 'provider_dispatch_performed": false' in src
 for marker in ('playwright','puppeteer','selenium','websocket','subprocess.run','requests.post'):
  assert marker not in src