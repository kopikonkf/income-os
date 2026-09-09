import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'product_planner.py'
spec=importlib.util.spec_from_file_location('product_planner',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

HP=ROOT/'company'/'h03'/'lib'/'h03_factory.py'
hspec=importlib.util.spec_from_file_location('h03_factory_product_test',HP); h03=importlib.util.module_from_spec(hspec); assert hspec.loader; hspec.loader.exec_module(h03)


class ProductPlannerTests(unittest.TestCase):
    def kp(self):
        return {
            'schema_version':'die.h03.knowledge-package.v1','knowledge_package_id':'KP-001','holding_id':'H03','version':1,'rights_status':'INTERNAL_ORIGINAL',
            'source_packet':{'source_id':'SRC-INT-001','rights_status':'INTERNAL_ORIGINAL','evidence_units':[{'evidence_id':'E1','text':'Step one is required.'},{'evidence_id':'E2','text':'Step two verifies the result.'},{'evidence_id':'E3','text':'Repeated input improves consistency.'}]},
            'claims':[{'claim_id':'C1','text':'Perform step one first.','evidence_refs':['E1']},{'claim_id':'C2','text':'Verify the result with step two.','evidence_refs':['E2']},{'claim_id':'C3','text':'Capture inputs consistently for repeated use.','evidence_refs':['E3']}]
        }
    def profile(self,shape='EXECUTE_SEQUENCE',**overrides):
        p={'schema_version':mod.PROFILE_SCHEMA,'planning_profile_id':'PLAN-001','holding_id':'H03','problem_seed_id':'H03-PS-A1','knowledge_package_id':'KP-001','desired_outcome':'complete the task correctly with less search and sequencing friction','delivery_shape':shape,'recurrence':'ONE_TIME','decision_complexity':'MEDIUM','explanation_depth':'MEDIUM','input_capture':'NONE','lookup_frequency':'LOW','evidence_density':'MEDIUM','reusable_structure':False,'section_plan':[{'heading':'Do the work','claim_ids':['C1','C2']}]}
        p.update(overrides); return p

    def test_sequential_outcome_selects_guide_not_ebook(self):
        s=mod.select_product_form(self.profile('EXECUTE_SEQUENCE'))
        self.assertEqual(s['form'],'guide')
        self.assertNotEqual(s['form'],'ebook')

    def test_quick_verify_selects_checklist(self):
        self.assertEqual(mod.select_product_form(self.profile('QUICK_VERIFY'))['form'],'checklist')

    def test_one_time_structured_input_selects_worksheet(self):
        p=self.profile('ONE_TIME_INPUT_WORKFLOW',input_capture='STRUCTURED')
        self.assertEqual(mod.select_product_form(p)['form'],'worksheet')

    def test_repeated_structured_input_selects_workbook(self):
        p=self.profile('REPEATED_INPUT_WORKFLOW',recurrence='REPEATED',input_capture='STRUCTURED')
        self.assertEqual(mod.select_product_form(p)['form'],'workbook')

    def test_complex_operation_selects_playbook(self):
        p=self.profile('COMPLEX_OPERATION',recurrence='REPEATED',decision_complexity='HIGH')
        self.assertEqual(mod.select_product_form(p)['form'],'playbook')

    def test_lookup_selects_reference_sheet(self):
        p=self.profile('LOOKUP_REFERENCE',lookup_frequency='HIGH',explanation_depth='LOW')
        self.assertEqual(mod.select_product_form(p)['form'],'reference_sheet')

    def test_evidence_decision_selects_report_or_research_brief_by_depth(self):
        high=self.profile('EVIDENCE_DECISION',evidence_density='HIGH',explanation_depth='HIGH')
        medium=self.profile('EVIDENCE_DECISION',evidence_density='MEDIUM',explanation_depth='MEDIUM')
        self.assertEqual(mod.select_product_form(high)['form'],'report')
        self.assertEqual(mod.select_product_form(medium)['form'],'research_brief')

    def test_reusable_output_selects_template(self):
        p=self.profile('REUSABLE_OUTPUT',reusable_structure=True,input_capture='STRUCTURED')
        self.assertEqual(mod.select_product_form(p)['form'],'template')

    def test_broad_learning_selects_handbook(self):
        self.assertEqual(mod.select_product_form(self.profile('BROAD_LEARNING',explanation_depth='HIGH'))['form'],'handbook')

    def test_ebook_requires_explicit_narrative_learning(self):
        self.assertEqual(mod.select_product_form(self.profile('NARRATIVE_LEARNING',explanation_depth='HIGH'))['form'],'ebook')
        for shape in ('EXECUTE_SEQUENCE','QUICK_VERIFY','COMPLEX_OPERATION','BROAD_LEARNING'):
            self.assertNotEqual(mod.select_product_form(self.profile(shape))['form'],'ebook')

    def test_form_maps_to_existing_template_registry(self):
        expected={'guide':'guide.clean.v1','playbook':'guide.clean.v1','report':'report.compact.v1','reference_sheet':'report.compact.v1','checklist':'worksheet.spacious.v1','workbook':'worksheet.spacious.v1','template':'worksheet.spacious.v1'}
        for form,template in expected.items():
            self.assertEqual(mod.select_template_for_form(form),template)

    def test_blueprint_uses_accepted_knowledge_and_compiles_with_existing_ast(self):
        kp=self.kp(); h03.validate_knowledge_package(kp)
        bp=mod.build_product_blueprint(product_id='PROD-001',title='Two-Step Verification Guide',profile=self.profile(),knowledge_package=kp,subtitle='A concise execution sequence')
        self.assertEqual(bp['schema_version'],'die.h03.product-blueprint.v1')
        self.assertEqual(bp['form'],'guide')
        self.assertIsNone(bp['metadata']['page_count_target'])
        ast=h03.compile_document_ast(kp,bp)
        self.assertEqual(ast['product_id'],'PROD-001')
        self.assertEqual(ast['metadata']['template_id'],'guide.clean.v1')

    def test_unknown_claim_in_section_fails_closed(self):
        p=self.profile(); p['section_plan'][0]['claim_ids']=['C-MISSING']
        with self.assertRaisesRegex(ValueError,'PRODUCT_PLANNING_UNKNOWN_CLAIM'):
            mod.build_product_blueprint(product_id='PROD-001',title='Bad',profile=p,knowledge_package=self.kp())

    def test_noncanonical_candidate_cannot_be_used_as_accepted_knowledge(self):
        candidate={'schema_version':'die.h03.knowledge-package-candidate.v1','knowledge_package_candidate_id':'KPC-1','holding_id':'H03','canonical_truth':False}
        with self.assertRaisesRegex(ValueError,'PRODUCT_BLUEPRINT_ACCEPTED_KNOWLEDGE_REQUIRED'):
            mod.build_product_blueprint(product_id='PROD-001',title='Bad',profile=self.profile(),knowledge_package=candidate)
