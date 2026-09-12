import json, subprocess, tempfile, unittest
import jsonschema
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MOD=ROOT/'company'/'company-os'/'die-h01'/'engineering'/'brave_udd_runtime.mjs'

def node(source):
    cp=subprocess.run(['node','--input-type=module','-e',source],text=True,capture_output=True,check=False)
    if cp.returncode!=0: raise AssertionError(cp.stderr)
    return json.loads(cp.stdout)

class BraveUddRuntimeTests(unittest.TestCase):
    def test_profile_mapping_edges(self):
        src=f'''import {{expectedBinding}} from {json.dumps(MOD.as_uri())}; console.log(JSON.stringify([1,5,6,10,96,100].map(n=>expectedBinding(n))))'''
        rows=node(src)
        self.assertEqual((rows[0]['udd_id'],rows[0]['cdp_port']),('h01-web-s01',9201))
        self.assertEqual((rows[1]['udd_id'],rows[1]['cdp_port']),('h01-web-s01',9205))
        self.assertEqual((rows[2]['udd_id'],rows[2]['cdp_port']),('h01-web-s02',9206))
        self.assertEqual((rows[-1]['udd_id'],rows[-1]['cdp_port']),('h01-web-s20',9300))

    def test_manifest_binding_fails_closed_on_non_loopback_or_mismatch(self):
        src=f'''import {{expectedBinding,resolveBinding}} from {json.dumps(MOD.as_uri())};
let r=expectedBinding(6),m={{schema:'die.h01.brave-fabric.host-local.v1',topology:{{max_active_per_udd:1}},profiles:[{{...r}}]}};
let ok=resolveBinding(m,'p006'); let errors=[];
for (const mutate of [x=>x.profiles[0].cdp_host='0.0.0.0',x=>x.profiles[0].udd_id='h01-web-s03']){{let z=JSON.parse(JSON.stringify(m));mutate(z);try{{resolveBinding(z,'p006')}}catch(e){{errors.push(e.code)}}}}
console.log(JSON.stringify({{ok,errors}}));'''
        v=node(src)
        self.assertEqual(v['ok']['profile_id'],'h01-web-p006')
        self.assertIn('E_MANIFEST_BINDING_MISMATCH',v['errors'])

    def test_terminal_result_identity_is_strict(self):
        src=f'''import {{validateTerminalResult}} from {json.dumps(MOD.as_uri())};
const c={{job_id:'j1',provider_id:'claude',profile_id:'h01-web-p001'}},good={{...c,terminal_state:'SUCCEEDED'}};let out=[];out.push(validateTerminalResult(good,c).terminal_state);
for(const bad of [{{...good,job_id:'x'}},{{...good,provider_id:'x'}},{{...good,profile_id:'x'}},{{...good,terminal_state:'RUNNING'}}]){{try{{validateTerminalResult(bad,c)}}catch(e){{out.push(e.code)}}}}console.log(JSON.stringify(out));'''
        out=node(src)
        self.assertEqual(out,['SUCCEEDED','E_RESULT_JOB_MISMATCH','E_RESULT_PROVIDER_MISMATCH','E_RESULT_PROFILE_MISMATCH','E_RESULT_NOT_TERMINAL'])

    def test_driver_owns_lifecycle_not_scheduler_or_secrets(self):
        s=MOD.read_text()
        for required in ('127.0.0.1','Browser.close','page_count_after_enforcement','launcher_udd_mutex','wait-result','probe'):
            self.assertIn(required,s)
        for forbidden in ('Network.getAllCookies','Storage.getCookies','document.cookie','mission.task.','mission_control.sqlite'):
            self.assertNotIn(forbidden,s)
        self.assertIn('mission_control_mutated:false',s)
        self.assertIn('scheduler_owned:false',s)

    def test_transient_target_url_is_reconciled_boundedly(self):
        s=MOD.read_text()
        self.assertIn('function targetOrigin',s)
        self.assertIn('const end=Date.now()+5000',s)
        self.assertIn("if(origin===wanted)return keep",s)
        self.assertNotIn("if(new URL(keep.url).origin!==wanted)",s)

    def test_live_receipts_and_sibling_exclusion_are_canonical(self):
        h=ROOT/'company/company-os/die-h01'
        rs=json.loads((h/'contracts/h01-brave-udd-runtime-receipt-v1.schema.json').read_text())
        js=json.loads((h/'contracts/h01-browser-job-result-v1.schema.json').read_text())
        for name in ('live-probe.runtime-receipt.json','live-wait-result.runtime-receipt.json'):
            v=json.loads((h/'fixtures/h01-025'/name).read_text()); jsonschema.Draft202012Validator(rs).validate(v)
            self.assertEqual(v['status'],'PASS'); self.assertTrue(v['browser']['loopback_only']); self.assertTrue(v['browser']['cdp_closed']); self.assertTrue(v['ownership']['lock_released'])
        probe=json.loads((h/'fixtures/h01-025/live-probe.job-result.json').read_text()); jsonschema.Draft202012Validator(js).validate(probe)
        sib=json.loads((h/'fixtures/h01-025/sibling-exclusion.json').read_text()); self.assertEqual(sib['attempt_exit_code'],73); self.assertEqual(sib['page_count_during_probe'],1)

    def test_graph_progression_after_h01_025(self):
        g=json.loads((ROOT/'company/company-os/die-h01/die-h01-task-graph.v1.json').read_text()); by={x['id']:x for x in g['tasks']}
        self.assertEqual(by['H01-025']['status'],'DONE')
        self.assertEqual(by['H01-107']['status'],'DONE')
        self.assertEqual(by['H01-107']['depends_on'],['H01-104A','H01-106','H01-025'])
        self.assertEqual(by['H01-026']['status'],'DONE')

if __name__=='__main__': unittest.main()
