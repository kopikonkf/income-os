from pathlib import Path
import importlib.util, sys, json, struct, zlib
ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
UP=load('prod_runtime_upscale',ROOT/'bridge/income_os_bridge/asset_upscale.py')
def png(path,w=2048,h=2048):
 def c(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d)&0xffffffff)
 raw=b''.join(b'\0'+b'\0\0\0\0'*w for _ in range(h));hdr=struct.pack('>IIBBBBB',w,h,8,6,0,0,0);path.write_bytes(b'\x89PNG\r\n\x1a\n'+c(b'IHDR',hdr)+c(b'IDAT',zlib.compress(raw))+c(b'IEND',b''))
def test_upscale_allows_pending_human_review_without_claiming_clearance(tmp_path):
 src=tmp_path/'a.png';png(src)
 policy={'schema':UP.POLICY_SCHEMA,'engine':'test','model_name':'x4','model_path':str(tmp_path/'missing'),'model_sha256':'0'*64,'scale':4,'tile':512,'tile_pad':10,'pre_pad':0,'half':False,'gpu_id':None,'backend_argv':[sys.executable]}
 r=UP.process(source=src,output=tmp_path/'out.png',policy=policy,min_width=1000,min_height=1000,min_megapixels=1,rights_state='PENDING_HUMAN_REVIEW',safety_state='PENDING_HUMAN_REVIEW')
 assert r['status']=='PASS' and r['action']=='NO_OP'
 assert r['rights_state']=='PENDING_HUMAN_REVIEW';assert r['authority_boundary']['submission_authorized'] is False
def test_installer_replaces_llm_cycle_with_no_agent_runtime_and_bounded_sudo():
 s=(ROOT/'company/die-agents/hermes/linux/install-production-cycle-v1.sh').read_text()
 assert '--no-agent' in s and 'production-runtime/production_runtime_tick.sh' in s
 assert 'gemini-3.7-flash' not in s and '--provider' not in s
 assert 'die-muxia-dispatch.service' in s and 'NOPASSWD' not in s and 'visudo -cf' not in s
def test_canonical_muxia_runner_and_dispatch_guard_exist():
 runner=(ROOT/'company/muxia/scripts/linux/muxia-chatgpt-image.mjs').read_text();guard=(ROOT/'company/muxia/scripts/linux/die-muxia-image-dispatch.py').read_text()
 assert 'prompt_submitted_by_automation' in runner and 'output_extracted_by_automation' in runner
 assert "len(sys.argv)!=2" in guard and "chatgpt-linux-a" in guard and "existing(task)" in guard
def test_runtime_stops_at_founder_qc_after_upscale():
 s=(ROOT/'company/die-agents/hermes/production-runtime/production_runtime_tick.py').read_text()
 for x in ['ARTIFACT_CREATED','WAITING_FOUNDER_QC','PENDING_HUMAN_REVIEW','PARKED_HUMAN_GATE','select_seed(DB,WORKSPACES)']:assert x in s
 assert 'asset_qc' not in s and 'rights_preflight' not in s


def test_gateway_sandbox_allows_only_cognition_receipt_write_paths():
    unit=(ROOT/'company/die-agents/hermes/linux/die-hermes-gateway.service').read_text()
    rw=next(line for line in unit.splitlines() if line.startswith('ReadWritePaths='))
    assert '/var/lib/die/division01/cognition-receipts' in rw
    assert '/var/lib/die/executive/cognition-receipts' in rw
    assert '/var/lib/die/division01 ' not in rw and '/var/lib/die/executive ' not in rw


def test_muxia_bridge_exports_verified_artifact_into_die_workspace():
    bridge=(ROOT/'company/muxia/scripts/linux/die-muxia-image-dispatch.py').read_text()
    assert 'def export_verified' in bridge
    assert "export_artifact_path" in bridge
    assert "DIE_GROUP='die-runtime'" in bridge
    assert 'os.chown' not in bridge
    assert "E_EXPORT_HASH" in bridge
    assert "private_artifact_access_by_hermes" in bridge

def test_runtime_consumes_export_not_private_muxia_artifact_and_preserves_progress():
    runtime=(ROOT/'company/die-agents/hermes/production-runtime/production_runtime_tick.py').read_text()
    assert "rec['export_artifact_path']" in runtime
    assert "rec.get('export_artifact_sha256')" in runtime
    assert "/var/lib/muxia/artifacts" not in runtime
    assert "prior=progress.read_bytes()" in runtime
    assert "progress.write_bytes(prior)" in runtime

def test_runtime_uses_queue_not_sudo_for_muxia_privilege_boundary():
    runtime=(ROOT/'company/die-agents/hermes/production-runtime/production_runtime_tick.py').read_text()
    assert 'die.muxia-dispatch-request.v1' in runtime
    assert 'MUXIA_QUEUE' in runtime
    assert 'sudo' not in runtime
    assert 'blueprint_sha256' in runtime


def test_muxia_queue_service_preserves_gateway_no_new_privileges():
    unit=(ROOT/'company/muxia/scripts/linux/die-muxia-dispatch.service').read_text()
    assert 'User=kopiko' in unit
    assert 'Group=die-runtime' in unit
    assert 'NoNewPrivileges=true' in unit
    assert '/var/lib/die/state/muxia-dispatch' in unit
    assert '/var/lib/muxia' in unit
    installer=(ROOT/'company/die-agents/hermes/linux/install-production-cycle-v1.sh').read_text()
    assert 'die-muxia-dispatch.service' in installer
    assert 'enable --now die-muxia-dispatch.service' in installer
    assert 'rm -f /etc/sudoers.d/die-hermes-muxia-image' in installer
    assert 'NOPASSWD' not in installer


def test_queue_worker_pins_blueprint_hash_and_validates_dispatch_result():
    worker=(ROOT/'company/muxia/scripts/linux/die-muxia-dispatch-worker.py').read_text()
    assert 'E_BLUEPRINT_LOCK_DRIFT' in worker
    assert 'export_artifact_sha256' in worker
    assert "payload.get('sha256')" in worker
    assert 'request_sha256' in worker


def test_muxia_dispatch_service_is_fully_unprivileged():
    unit=(ROOT/'company/muxia/scripts/linux/die-muxia-dispatch.service').read_text()
    dispatch=(ROOT/'company/muxia/scripts/linux/die-muxia-image-dispatch.py').read_text()
    assert 'User=kopiko' in unit and 'Group=die-runtime' in unit
    assert 'NoNewPrivileges=true' in unit
    assert 'runuser' not in dispatch
    assert "E_SERVICE_IDENTITY" in dispatch
    assert "MUXIA_USER='kopiko'" in dispatch
    assert 'os.chown' not in dispatch
