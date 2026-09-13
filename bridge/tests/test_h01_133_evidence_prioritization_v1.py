import importlib.util,json,sys,unittest
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'company/company-os/die-h01/lib/evidence_prioritization.py'
SCHEMA=json.loads((ROOT/'company/company-os/die-h01/contracts/h01-evidence-prioritization.v1.schema.json').read_text())
S=importlib.util.spec_from_file_location('h133',LIB); M=importlib.util.module_from_spec(S); assert S and S.loader; sys.modules[S.name]=M; S.loader.exec_module(M)
def d(q,s,c,f=None):
 x={'rank_state':'RANKED','rank_score':s,'confidence':c,'evidence_refs':[{'evidence_id':'SIG-'+q}],'discoveries':{'family_hypotheses':[]}}
 if f:x['discoveries']['family_hypotheses']=[{'kind':'FAMILY','label':f,'status':'HYPOTHESIS','evidence_ids':['SIG-'+q]}]
 return x
def c(q,i):return {'evidence_id':'COMP-'+q,'freshness':'FRESH','normalized_metrics':{'competition_index':i}}
class T(unittest.TestCase):
 def setUp(self):self.q=[{'queue_item_id':'H01-SVGQ-A','canonical_name':'shopping bag'},{'queue_item_id':'H01-SVGQ-B','canonical_name':'cable organizer'},{'queue_item_id':'H01-SVGQ-C','canonical_name':'trophy'}]
 def test_rank_and_schema(self):
  r=M.prioritize(self.q,demand_records={'H01-SVGQ-A':d('A',.8,'HIGH','packing'),'H01-SVGQ-B':d('B',.6,'MEDIUM','packing')},connector_evidence={'H01-SVGQ-A':[c('A',80)],'H01-SVGQ-B':[c('B',20)]}); jsonschema.Draft202012Validator(SCHEMA).validate(r); self.assertEqual([x['queue_item_id'] for x in r['remaining_ranked'][:2]],['H01-SVGQ-A','H01-SVGQ-B']); self.assertFalse(r['family_rankings'][0]['canonical_family_promotion_authorized'])
 def test_produced_preserved(self):
  r=M.prioritize(self.q,demand_records={'H01-SVGQ-A':d('A',1,'HIGH')},produced_queue_item_ids={'H01-SVGQ-A'}); p=r['produced_preserved'][0]; self.assertEqual(p['rank_state'],'NOT_RERANKED'); self.assertIsNone(p['priority_score']); self.assertEqual(p['effects']['produced_master_validity_effect'],'NONE'); self.assertFalse(r['policy']['already_produced_masters_invalidated'])
 def test_unranked_stays_valid(self):
  r=M.prioritize(self.q,demand_records={'H01-SVGQ-C':d('C',.4,'LOW')}); self.assertEqual([x['queue_item_id'] for x in r['remaining_ranked']],['H01-SVGQ-C','H01-SVGQ-A','H01-SVGQ-B']); self.assertTrue(r['policy']['unranked_items_remain_production_valid']); self.assertIsNone(r['remaining_ranked'][1]['priority_score'])
if __name__=='__main__':unittest.main()
