import copy, importlib.util, json, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ENG=ROOT/'company'/'company-os'/'die-h01'/'engineering'
sys.path.insert(0,str(ENG))
import native_svg_request_contract as C
import svg_prompt_composer_v2 as P

BP_PATH=ROOT/'company'/'company-os'/'die-h01'/'fixtures'/'h01-102-book-blueprint.v2.json'

class NativeSvgContractTests(unittest.TestCase):
    def setUp(self):
        self.bp=json.loads(BP_PATH.read_text())
        self.master,self.prompt=P.compile_pipeline(blueprint=self.bp,provider_profile='CLAUDE_WEB')
        self.req=C.build_request(
            request_id='H01SVGREQ-BOOK_001',queue_item_id=self.bp['queue_id'],source_candidate_id=self.bp['source_candidate_id'],semantic_asset_id=self.bp['semantic_asset_id'],
            provider_id='claude',provider_profile=self.prompt['provider_profile'],blueprint_id=self.bp['blueprint_id'],blueprint_sha256=self.prompt['blueprint_sha256'],
            master_instruction_sha256=self.prompt['master_instruction_sha256'],provider_prompt=self.prompt['prompt'],provider_prompt_sha256=self.prompt['prompt_sha256'])
        self.svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="15" y="20" width="70" height="55" fill="#336699"/></svg>'
        self.canon='a'*64

    def test_default_ingress_is_web_adapter_and_native_mcp_is_optional(self):
        self.assertEqual(self.req['ingress_policy'],{'preferred':'WEB_AI_ADAPTER','allowed':['WEB_AI_ADAPTER','NATIVE_MCP'],'native_mcp_required':False})
        self.assertEqual(self.req['authority']['dispatch_semantics'],'EXACTLY_ONCE')
        self.assertFalse(self.req['authority']['submission_authorized']); self.assertFalse(self.req['authority']['publication_authorized'])

    def test_request_preserves_h01_102_hash_chain_and_prompt(self):
        self.assertEqual(self.req['blueprint']['sha256'],self.prompt['blueprint_sha256'])
        self.assertEqual(self.req['master_instruction_sha256'],self.prompt['master_instruction_sha256'])
        self.assertEqual(self.req['prompt']['sha256'],self.prompt['prompt_sha256'])
        self.assertEqual(self.req['prompt']['text'],self.prompt['prompt']); C.validate_request(self.req)

    def test_request_is_provider_generic_not_claude_schema(self):
        q=copy.deepcopy(self.req); q['request_id']='H01SVGREQ-BOOK_QWEN'; q['provider_target']={'provider_id':'qwen','provider_profile':'QWEN_WEB'}
        q['idempotency_key']=C.sha256_value(C._request_idempotency_material(q)); C.validate_request(q)
        self.assertEqual(q['schema'],'die.h01.native-svg-request.v1'); self.assertNotEqual(q['idempotency_key'],self.req['idempotency_key'])

    def test_prompt_or_idempotency_tamper_fails_closed(self):
        bad=copy.deepcopy(self.req); bad['prompt']['text']+=' x'
        with self.assertRaisesRegex(C.NativeSvgContractError,'PROMPT_CHAR_COUNT_MISMATCH|PROMPT_HASH_MISMATCH'): C.validate_request(bad)
        bad=copy.deepcopy(self.req); bad['idempotency_key']='0'*64
        with self.assertRaisesRegex(C.NativeSvgContractError,'IDEMPOTENCY_KEY_MISMATCH'): C.validate_request(bad)

    def test_normalizer_accepts_fence_but_rejects_prose_or_non_svg(self):
        self.assertEqual(C.normalize_svg_payload('```svg\n'+self.svg+'\n```'),self.svg)
        with self.assertRaisesRegex(C.NativeSvgContractError,'PROVIDER_RESPONSE_INVALID'): C.normalize_svg_payload('Here: '+self.svg)
        with self.assertRaisesRegex(C.NativeSvgContractError,'OUTPUT_NOT_SVG'): C.normalize_svg_payload('not svg')

    def test_success_receipt_preserves_provider_result_and_native_claim(self):
        r=C.build_success_receipt(request=self.req,ingress='WEB_AI_ADAPTER',dispatch_commit_id='dispatch-book-001',provider_status='COMPLETED',provider_response_text=self.svg,h01_103_canonical_svg_sha256=self.canon,provider_request_id='provider-123',finish_reason='STOP')
        self.assertEqual(r['status'],'SUCCEEDED'); self.assertEqual(r['lineage']['prompt_sha256'],self.prompt['prompt_sha256'])
        self.assertEqual(r['provider_result']['provider_request_id'],'provider-123'); self.assertEqual(r['provider_result']['candidate_svg_sha256'],C.sha256_text(self.svg))
        self.assertEqual(r['native_svg_claim'],{'source_kind':'DIRECT_PROVIDER_SVG_SOURCE','native_editable':True,'conversion_from_raster':False,'embedded_raster':False,'success_claim_allowed':True})
        self.assertEqual(r['validation'],{'engine':'H01-103','status':'PASS','canonical_svg_sha256':self.canon})

    def test_success_cannot_claim_raster_trace_or_skip_h01_103(self):
        r=C.build_success_receipt(request=self.req,ingress='WEB_AI_ADAPTER',dispatch_commit_id='dispatch-book-001',provider_status='COMPLETED',provider_response_text=self.svg,h01_103_canonical_svg_sha256=self.canon)
        bad=copy.deepcopy(r); bad['native_svg_claim']['conversion_from_raster']=True
        with self.assertRaisesRegex(C.NativeSvgContractError,'RASTER_TRACE_SUCCESS_FORBIDDEN'): C.validate_receipt(bad,request=self.req)
        bad=copy.deepcopy(r); bad['validation']={'engine':'H01-103','status':'NOT_RUN','canonical_svg_sha256':None}
        with self.assertRaisesRegex(C.NativeSvgContractError,'H01_103_PASS_REQUIRED'): C.validate_receipt(bad,request=self.req)

    def test_failure_receipt_preserves_provider_failure_without_svg_success(self):
        r=C.build_failure_receipt(request=self.req,ingress='WEB_AI_ADAPTER',dispatch_commit_id='dispatch-book-002',status='TIMEOUT',provider_status='TIMED_OUT',error_code='PROVIDER_TIMEOUT',error_detail='bounded provider wait expired',provider_request_id='provider-456')
        self.assertEqual(r['status'],'TIMEOUT'); self.assertEqual(r['provider_result']['error_code'],'PROVIDER_TIMEOUT')
        self.assertFalse(r['native_svg_claim']['success_claim_allowed']); self.assertEqual(r['validation']['status'],'NOT_RUN')

    def test_exactly_once_ledger_commits_one_ingress_only(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=C.ExactlyOnceLedger(td)
            s,_=ledger.reserve(self.req); self.assertEqual(s,'CREATED')
            s,_=ledger.reserve(self.req); self.assertEqual(s,'UNCHANGED')
            s,_=ledger.commit_dispatch(self.req,ingress='WEB_AI_ADAPTER',dispatch_commit_id='dispatch-book-003'); self.assertEqual(s,'COMMITTED')
            s,_=ledger.commit_dispatch(self.req,ingress='WEB_AI_ADAPTER',dispatch_commit_id='dispatch-book-003'); self.assertEqual(s,'UNCHANGED')
            with self.assertRaisesRegex(C.NativeSvgContractError,'E_ALREADY_DISPATCHED'):
                ledger.commit_dispatch(self.req,ingress='NATIVE_MCP',dispatch_commit_id='dispatch-book-004')

    def test_semantic_replay_with_new_request_id_does_not_authorize_second_dispatch(self):
        replay=copy.deepcopy(self.req); replay['request_id']='H01SVGREQ-BOOK_REPLAY'
        C.validate_request(replay); self.assertEqual(replay['idempotency_key'],self.req['idempotency_key'])
        with tempfile.TemporaryDirectory() as td:
            ledger=C.ExactlyOnceLedger(td)
            ledger.commit_dispatch(self.req,ingress='WEB_AI_ADAPTER',dispatch_commit_id='dispatch-book-005')
            s,row=ledger.reserve(replay); self.assertEqual(s,'UNCHANGED'); self.assertEqual(row['request_id'],self.req['request_id'])
            with self.assertRaisesRegex(C.NativeSvgContractError,'E_ALREADY_DISPATCHED'):
                ledger.commit_dispatch(replay,ingress='NATIVE_MCP',dispatch_commit_id='dispatch-book-006')

    def test_terminal_receipt_is_idempotent_and_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=C.ExactlyOnceLedger(td); ledger.commit_dispatch(self.req,ingress='WEB_AI_ADAPTER',dispatch_commit_id='dispatch-book-007')
            r=C.build_success_receipt(request=self.req,ingress='WEB_AI_ADAPTER',dispatch_commit_id='dispatch-book-007',provider_status='COMPLETED',provider_response_text=self.svg,h01_103_canonical_svg_sha256=self.canon)
            s,_=ledger.commit_terminal(self.req,r); self.assertEqual(s,'COMMITTED')
            s,_=ledger.commit_terminal(self.req,r); self.assertEqual(s,'UNCHANGED')
            changed=copy.deepcopy(r); changed['provider_result']['finish_reason']='DIFFERENT'
            with self.assertRaisesRegex(C.NativeSvgContractError,'TERMINAL_RECEIPT_CONFLICT'): ledger.commit_terminal(self.req,changed)

    def test_terminal_receipt_requires_dispatch_commit(self):
        r=C.build_success_receipt(request=self.req,ingress='WEB_AI_ADAPTER',dispatch_commit_id='dispatch-book-008',provider_status='COMPLETED',provider_response_text=self.svg,h01_103_canonical_svg_sha256=self.canon)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(C.NativeSvgContractError,'DISPATCH_COMMIT_REQUIRED'): C.ExactlyOnceLedger(td).commit_terminal(self.req,r)

    def test_native_mcp_uses_same_contract_and_does_not_change_semantic_identity(self):
        r=C.build_success_receipt(request=self.req,ingress='NATIVE_MCP',dispatch_commit_id='dispatch-book-009',provider_status='COMPLETED',provider_response_text=self.svg,h01_103_canonical_svg_sha256=self.canon)
        self.assertEqual(r['schema'],'die.h01.native-svg-receipt.v1'); self.assertEqual(r['idempotency_key'],self.req['idempotency_key']); self.assertEqual(r['semantic_asset_id'],self.req['semantic_asset_id'])


    def test_canonical_fixtures_validate_and_are_explicitly_synthetic(self):
        base=ROOT/'company'/'company-os'/'die-h01'/'fixtures'/'h01-104'
        req=json.loads((base/'request.web-ai-adapter.json').read_text()); ok=json.loads((base/'receipt.success.synthetic.json').read_text()); fail=json.loads((base/'receipt.timeout.synthetic.json').read_text())
        C.validate_request(req); C.validate_receipt(ok,request=req); C.validate_receipt(fail,request=req)
        self.assertEqual(ok['provider_result']['provider_request_id'],'FIXTURE-NOT-LIVE')
        self.assertIn('synthetic contract fixture only',fail['provider_result']['error_detail'])

    def test_contract_contains_no_credential_or_session_fields(self):
        raw=(C.REQUEST_SCHEMA.read_text()+C.RECEIPT_SCHEMA.read_text()).casefold()
        for token in ('cookie','access_token','refresh_token','mission_lease_token','review_token','password','session_bytes'):
            self.assertNotIn(token,raw)

if __name__=='__main__': unittest.main()
