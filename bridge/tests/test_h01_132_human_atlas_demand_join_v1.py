import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'company/company-os/die-h01/lib/human_atlas_demand_join.py'
SCHEMA=json.loads((ROOT/'company/company-os/die-h01/contracts/h01-human-atlas-demand-context.v1.schema.json').read_text())
S=importlib.util.spec_from_file_location('h01_132_join',LIB); M=importlib.util.module_from_spec(S); assert S and S.loader; sys.modules[S.name]=M; S.loader.exec_module(M)
class H01132HumanAtlasJoin(unittest.TestCase):
    def test_known_object_returns_bounded_hypothesis_context(self):
        r=M.join('H01-SVGQ-CAND-TEST','shopping bag',source_candidate_id='CAND-TEST',limit=5)
        jsonschema.Draft202012Validator(SCHEMA).validate(r)
        self.assertEqual(r['join_state'],'CONTEXT_AVAILABLE'); self.assertLessEqual(r['retrieval']['result_count'],5)
        self.assertEqual(r['contexts'][0]['context_id'],'HCTX-SMALL-BUSINESS-PACKAGING-001')
        self.assertIn('small business seller',r['contexts'][0]['human']); self.assertIn('packing customer orders',r['contexts'][0]['activity'])
        self.assertFalse(r['policy']['market_evidence']); self.assertTrue(r['policy']['supply_first_independent']); self.assertEqual(r['policy']['rank_authority'],'NONE')
    def test_unknown_object_is_nonblocking_no_context(self):
        r=M.join('H01-SVGQ-CAND-UNKNOWN','xyzzynonexistentobject',limit=3)
        jsonschema.Draft202012Validator(SCHEMA).validate(r); self.assertEqual(r['join_state'],'NO_CONTEXT'); self.assertEqual(r['contexts'],[])
        self.assertEqual(r['effects']['standalone_production_blocking_effect'],'NONE')
    def test_deterministic_and_identity_preserving(self):
        a=M.join('H01-SVGQ-CAND-1','cable organizer',source_candidate_id='CAND-1',limit=4); b=M.join('H01-SVGQ-CAND-1','cable organizer',source_candidate_id='CAND-1',limit=4)
        self.assertEqual(a,b); self.assertEqual(a['queue_item_id'],'H01-SVGQ-CAND-1'); self.assertEqual(a['effects']['queue_identity_effect'],'NONE')
        self.assertEqual(a['contexts'][0]['context_id'],'HCTX-REMOTE-WORK-CABLE-001')
    def test_limit_is_stricter_than_legacy_registry_limit(self):
        with self.assertRaisesRegex(M.HumanAtlasJoinError,'E_CONTEXT_LIMIT'): M.join('H01-SVGQ-X','trophy',limit=13)
    def test_no_authority_expansion(self):
        r=M.join('H01-SVGQ-CAND-2','trophy',limit=3)
        self.assertTrue(all(v is False for v in r['authority'].values())); self.assertTrue(all(v=='NONE' for v in r['effects'].values()))
if __name__=='__main__': unittest.main()
