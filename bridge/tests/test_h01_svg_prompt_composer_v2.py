import ast, copy, json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
ENG=ROOT/'company'/'company-os'/'die-h01'/'engineering'
sys.path.insert(0,str(ENG))
import svg_prompt_composer_v2 as C
FIX=ROOT/'company'/'company-os'/'die-h01'/'fixtures'/'h01-102-book-blueprint.v2.json'
BP_SCHEMA=ROOT/'company'/'company-os'/'die-h01'/'contracts'/'h01-svg-blueprint-v2.schema.json'
PROFILES=ROOT/'company'/'company-os'/'die-h01'/'runtime'/'h01-svg-prompt-profiles.v2.json'
SVG_SOURCE=ROOT/'company'/'factory-asset'/'lib'/'native_svg_pipeline.py'

class PromptComposerTests(unittest.TestCase):
    def setUp(self): self.bp=json.loads(FIX.read_text())

    def test_blueprint_is_fixed_h01_supply_contract_and_provider_independent(self):
        C.validate_blueprint(self.bp)
        self.assertEqual(self.bp['production_contract'],{'media':'VECTOR','mode':'VECTOR_OBJECT','form':'SINGLE','preset':'CLEAN_STOCK_VECTOR_V1'})
        raw=json.dumps(self.bp).casefold()
        for token in ('provider_profile','provider_id','transport','temperature','max_tokens','system_prompt'): self.assertNotIn(token,raw)
        bad=copy.deepcopy(self.bp); bad['provider_profile']='CLAUDE_WEB'
        with self.assertRaisesRegex(C.SvgPromptError,'BLUEPRINT_SCHEMA_INVALID'): C.validate_blueprint(bad)

    def test_master_instruction_is_provider_neutral_and_hash_stable(self):
        a=C.compile_master_instruction(self.bp); b=C.compile_master_instruction(copy.deepcopy(self.bp))
        self.assertEqual(a,b); self.assertEqual(a['master_instruction_sha256'],b['master_instruction_sha256'])
        raw=json.dumps(a).casefold()
        for token in ('claude_web','qwen_web','chatgpt_web','gemini_web','manus_web','browser_cdp'): self.assertNotIn(token,raw)
        self.assertEqual([s['name'] for s in a['sections']],['SUBJECT','COMMERCIAL','COMPOSITION','VECTOR_STYLE','COMPLEXITY','RIGHTS_AND_STOCK','SVG_OUTPUT'])

    def test_all_provider_profiles_preserve_same_master_semantics_within_budget(self):
        master=C.compile_master_instruction(self.bp); registry=json.loads(PROFILES.read_text()); hashes=set()
        for row in registry['profiles']:
            out=C.compile_provider_prompt(blueprint=self.bp,master=master,provider_profile=row['provider_profile'])
            self.assertLessEqual(out['prompt_chars'],out['prompt_budget_chars']); self.assertEqual(out['semantic_omission_count'],0)
            self.assertEqual(out['master_instruction_sha256'],master['master_instruction_sha256']); self.assertFalse(out['authority']['provider_call_authorized']); hashes.add(out['prompt_sha256'])
            text=out['prompt'].casefold()
            for section in master['sections']:
                for clause in section['clauses']: self.assertIn(clause.casefold(),text)
        self.assertGreater(len(hashes),1)

    def test_budget_exceeded_fails_instead_of_truncating_semantics(self):
        master=C.compile_master_instruction(self.bp)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'profiles.json'; p.write_text(json.dumps({'schema':'die.h01.svg-prompt-profiles.v2','revision':'2.0.0','budget_semantics':'TEST','profiles':[{'provider_profile':'TINY','prompt_budget_chars':1000,'opening':'Make SVG.','closing':'Raw SVG only.'}]}))
            with mock.patch.object(C,'PROFILE_PATH',p):
                with self.assertRaisesRegex(C.SvgPromptError,'PROVIDER_PROMPT_BUDGET_EXCEEDED'): C.compile_provider_prompt(blueprint=self.bp,master=master,provider_profile='TINY')

    def test_master_tamper_fails_closed(self):
        master=C.compile_master_instruction(self.bp); master['sections'][0]['clauses'][0]='Different subject'
        with self.assertRaisesRegex(C.SvgPromptError,'MASTER_HASH_MISMATCH'): C.compile_provider_prompt(blueprint=self.bp,master=master,provider_profile='GENERIC_WEB_AI')

    def test_commercial_vector_svg_constraints_survive_prompt(self):
        _,prompt=C.compile_pipeline(blueprint=self.bp,provider_profile='GENERIC_WEB_AI'); text=prompt['prompt'].casefold()
        for required in ('book','recognition anchors','primary use','buyer value','visual hierarchy','native editable vector geometry','svg bytes <=','no logos or trademarks','transparent background','allowed path commands','embedded raster image','foreignobject','raw svg source only'):
            self.assertIn(required,text)
        self.assertIn('m; l; h; v; c; s; q; t; a; z',text)

    def test_blueprint_complexity_ceiling_never_exceeds_h01_103_engine(self):
        schema=json.loads(BP_SCHEMA.read_text())['properties']['complexity']['properties']
        tree=ast.parse(SVG_SOURCE.read_text()); defaults={}; group_depth=None
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MAX_GROUP_DEPTH' for t in node.targets): group_depth=ast.literal_eval(node.value)
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name=='validate_and_normalize':
                args=node.args.args+node.args.kwonlyargs; vals=[None]*(len(args)-len(node.args.defaults)-len(node.args.kw_defaults))+node.args.defaults+node.args.kw_defaults
                for a,v in zip(args,vals):
                    if a.arg in {'max_bytes','max_paths','max_total_points','max_path_chars'} and v is not None: defaults[a.arg]=ast.literal_eval(v)
        self.assertLessEqual(schema['max_svg_bytes']['maximum'],defaults['max_bytes'])
        self.assertLessEqual(schema['max_geometry_elements']['maximum'],defaults['max_paths'])
        self.assertLessEqual(schema['max_total_points']['maximum'],defaults['max_total_points'])
        self.assertLessEqual(schema['max_path_chars']['maximum'],defaults['max_path_chars'])
        self.assertLessEqual(schema['max_group_depth']['maximum'],group_depth)

    def test_forbidden_svg_contract_matches_h01_103_subset(self):
        forbidden=set(self.bp['output_contract']['forbidden_svg_features'])
        for item in ('script','embedded raster image','foreignObject','text','style','defs','symbol','use'): self.assertIn(item,forbidden)
        self.assertEqual(self.bp['output_contract']['allowed_elements'],['g','path','rect','circle','ellipse','line','polyline','polygon'])
        self.assertEqual(self.bp['output_contract']['allowed_path_commands'],['M','L','H','V','C','S','Q','T','A','Z'])

    def test_pipeline_deterministic(self):
        m1,p1=C.compile_pipeline(blueprint=self.bp,provider_profile='CLAUDE_WEB'); m2,p2=C.compile_pipeline(blueprint=copy.deepcopy(self.bp),provider_profile='CLAUDE_WEB')
        self.assertEqual(m1,m2); self.assertEqual(p1,p2)

if __name__=='__main__': unittest.main()
