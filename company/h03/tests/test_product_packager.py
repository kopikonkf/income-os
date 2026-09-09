import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'product_packager.py'
spec=importlib.util.spec_from_file_location('product_packager',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

class ProductPackagerTests(unittest.TestCase):
    def kp(self):
        return {'schema_version':'die.h03.knowledge-package.v1','knowledge_package_id':'KP-001','holding_id':'H03','version':1,'rights_status':'INTERNAL_ORIGINAL','source_packet':{'source_id':'SRC-1','rights_status':'INTERNAL_ORIGINAL','evidence_units':[{'evidence_id':'E1','text':'Step one.'},{'evidence_id':'E2','text':'Step two.'},{'evidence_id':'E3','text':'Verify completion.'}]},'claims':[{'claim_id':'C1','text':'Perform step one first.','evidence_refs':['E1']},{'claim_id':'C2','text':'Then perform step two.','evidence_refs':['E2']},{'claim_id':'C3','text':'Verify the result.','evidence_refs':['E3']}]}
    def blueprint(self,form='guide',template='guide.clean.v1'):
        return {'schema_version':'die.h03.product-blueprint.v1','product_id':'PROD-001','knowledge_package_id':'KP-001','form':form,'title':'Two-Step Verification Guide','subtitle':'A bounded useful product','sections':[{'heading':'Do the work','claim_ids':['C1','C2']},{'heading':'Verify','claim_ids':['C3']}],'metadata':{'template_id':template,'desired_outcome':'complete the task correctly','page_count_target':None}}
    def batches(self):
        return [
            {'schema_version':'die.h03.content-block-batch.v1','content_batch_id':'CB-1','holding_id':'H03','product_id':'PROD-001','knowledge_package_id':'KP-001','section_id':'SEC-001','section_heading':'Do the work','producer_observation':{'provider_id':'qwen'},'blocks':[{'block_id':'B1','kind':'STEP','text':'Perform step one first.','claim_ids':['C1'],'evidence_refs':['E1']},{'block_id':'B2','kind':'STEP','text':'Then perform step two.','claim_ids':['C2'],'evidence_refs':['E2']}],'truth_status':'DERIVED_SEMANTIC_CONTENT'},
            {'schema_version':'die.h03.content-block-batch.v1','content_batch_id':'CB-2','holding_id':'H03','product_id':'PROD-001','knowledge_package_id':'KP-001','section_id':'SEC-002','section_heading':'Verify','producer_observation':{'provider_id':'gemini'},'blocks':[{'block_id':'B3','kind':'CHECKLIST_ITEM','text':'Verify the result.','claim_ids':['C3'],'evidence_refs':['E3']}],'truth_status':'DERIVED_SEMANTIC_CONTENT'}
        ]

    def test_content_batches_must_cover_every_blueprint_claim(self):
        b=self.batches(); b[0]['blocks']=b[0]['blocks'][:1]
        with self.assertRaisesRegex(ValueError,'SECTION_CLAIM_COVERAGE_MISSING:C2'):
            mod.validate_content_batches(blueprint=self.blueprint(),knowledge_package=self.kp(),content_batches=b)

    def test_evidence_refs_are_revalidated_from_accepted_knowledge(self):
        b=self.batches(); b[0]['blocks'][0]['evidence_refs']=['E999']
        with self.assertRaisesRegex(ValueError,'BLOCK_EVIDENCE_MISMATCH'):
            mod.validate_content_batches(blueprint=self.blueprint(),knowledge_package=self.kp(),content_batches=b)

    def test_semantic_blocks_compile_to_existing_document_ast(self):
        ast=mod.assemble_document_ast(blueprint=self.blueprint(),knowledge_package=self.kp(),content_batches=self.batches())
        self.assertEqual(ast['schema_version'],'die.h03.document-ast.v1')
        self.assertEqual(ast['blocks'][0],{'type':'heading','text':'Do the work'})
        self.assertEqual(ast['blocks'][1]['type'],'bullet')
        self.assertTrue(ast['blocks'][1]['text'].startswith('1. '))
        self.assertIn('[ ] ',ast['blocks'][-1]['text'])
        self.assertEqual(len(ast['metadata']['content_lineage']),3)

    def test_local_product_package_is_deterministic_and_not_published(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            r1=mod.build_local_product_package(output_root=Path(a),blueprint=self.blueprint(),knowledge_package=self.kp(),content_batches=self.batches())
            r2=mod.build_local_product_package(output_root=Path(b),blueprint=self.blueprint(),knowledge_package=self.kp(),content_batches=self.batches())
            self.assertEqual(r1['pdf_sha256'],r2['pdf_sha256'])
            self.assertEqual(r1['zip_sha256'],r2['zip_sha256'])
            self.assertGreaterEqual(r1['page_count'],1)
            self.assertFalse(r1['external_publication'])
            self.assertEqual(r1['status'],'LOCAL_SALE_READY_UNREVIEWED')
            p=Path(a)/'PROD-001'
            self.assertTrue((p/r1['pdf_file']).exists())
            self.assertTrue((p/r1['zip_file']).exists())
            self.assertTrue((p/'manifest.json').exists())
            manifest=json.loads((p/'manifest.json').read_text(encoding='utf-8'))
            self.assertIn(r1['pdf_file'],manifest['files'])
            self.assertNotIn('package-receipt.json',manifest['files'])

    def test_package_receipt_contains_no_external_action_or_credentials(self):
        with tempfile.TemporaryDirectory() as a:
            r=mod.build_local_product_package(output_root=Path(a),blueprint=self.blueprint(),knowledge_package=self.kp(),content_batches=self.batches())
            text=json.dumps(r).lower()
            self.assertNotIn('token',text)
            self.assertNotIn('cookie',text)
            self.assertFalse(r['external_publication'])
