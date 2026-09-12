import hashlib,json,sqlite3,sys,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'company'/'company-os'/'die-h01'/'lib'
sys.path.insert(0,str(LIB))
import taxonomy_family_mapper_v1 as M
from semantic_family_v1 import validate_semantic_family

def make_db(path:Path, rows:list[tuple]):
    con=sqlite3.connect(path)
    con.execute('''CREATE TABLE candidate_seeds(id TEXT PRIMARY KEY,raw_noun_id INTEGER,canonical_name TEXT,aliases TEXT,wordnet_synsets TEXT,suitability TEXT,ip_risk TEXT,wave3_status TEXT)''')
    con.executemany('INSERT INTO candidate_seeds VALUES(?,?,?,?,?,?,?,?)',rows); con.commit(); con.close()

def row(cid,rid,name,synset,*,aliases='[]',status='eligible',suit='lexname=noun.artifact'):
    return (cid,rid,name,aliases,json.dumps([synset]),suit,'none',status)

class TaxonomyFamilyMapperTests(unittest.TestCase):
    def setUp(self): self.t=tempfile.TemporaryDirectory(); self.root=Path(self.t.name)
    def tearDown(self): self.t.cleanup()

    def test_primary_synset_creates_taxonomic_family_and_preserves_identity(self):
        db=self.root/'a.db'; make_db(db,[row('CAND-001',1,'merchandise','merchandise.n.01'),row('CAND-002',2,'wares','merchandise.n.01'),row('CAND-003',3,'book','book.n.01')])
        r=M.map_taxonomy_families(M._read_rows(db),db_ref=str(db)); self.assertEqual(r['family_count'],1); self.assertEqual(r['family_member_count'],2); self.assertEqual(r['standalone_singleton_count'],1)
        f=r['families'][0]; validate_semantic_family(f); self.assertEqual(f['family_class'],'TAXONOMIC'); self.assertEqual(f['semantic_identity']['semantic_key'],'wordnet.primary.merchandise.n.01')
        self.assertEqual([m['member_id'] for m in f['members']],['CAND-001','CAND-002']); self.assertTrue(all(m['identity_effect']=='NONE' for m in f['members'])); self.assertEqual(f['rights_class'],'REVIEW_REQUIRED')

    def test_standalone_subject_is_never_rewritten_or_forced_into_family(self):
        rows=[row('CAND-001',1,'book','book.n.01'),row('CAND-002',2,'cat','cat.n.01')]
        r=M.map_taxonomy_families([dict(zip(['id','raw_noun_id','canonical_name','aliases','wordnet_synsets','suitability','ip_risk','wave3_status'],x)) for x in rows],db_ref='fixture.db')
        self.assertEqual(r['family_count'],0); self.assertEqual(r['standalone_singleton_count'],2); self.assertTrue(r['controls']['standalone_identity_preserved'])

    def test_alias_collision_is_observation_not_merge_authority(self):
        db=self.root/'b.db'; make_db(db,[row('CAND-001',1,'cat','cat.n.01',aliases='["kitty"]'),row('CAND-002',2,'kitty','cat.n.01')])
        r=M.map_taxonomy_families(M._read_rows(db),db_ref=str(db)); self.assertEqual(len(r['alias_observations']),1); obs=r['alias_observations'][0]
        self.assertEqual(obs['normalized_term'],'kitty'); self.assertEqual(obs['subject_ids'],['CAND-001','CAND-002']); self.assertFalse(obs['merge_authorized']); self.assertEqual(len(r['families'][0]['members']),2)

    def test_duplicate_normalized_canonical_name_fails_closed(self):
        db=self.root/'c.db'; make_db(db,[row('CAND-001',1,'Book','book.n.01'),row('CAND-002',2,' book ','book.n.01')])
        with self.assertRaisesRegex(M.TaxonomyFamilyMapError,'E_DUPLICATE_CANONICAL_NAME'): M.map_taxonomy_families(M._read_rows(db),db_ref=str(db))

    def test_duplicate_raw_noun_id_fails_closed(self):
        db=self.root/'d.db'; make_db(db,[row('CAND-001',1,'book','book.n.01'),row('CAND-002',1,'volume','book.n.01')])
        with self.assertRaisesRegex(M.TaxonomyFamilyMapError,'E_DUPLICATE_RAW_NOUN_ID'): M.map_taxonomy_families(M._read_rows(db),db_ref=str(db))

    def test_export_is_deterministic_and_source_db_stays_unchanged(self):
        db=self.root/'e.db'; make_db(db,[row('CAND-003',3,'book','book.n.01'),row('CAND-001',1,'wares','merchandise.n.01'),row('CAND-002',2,'merchandise','merchandise.n.01')])
        before=hashlib.sha256(db.read_bytes()).hexdigest(); a=M.export_taxonomy_families(db_path=db,output_dir=self.root/'out-a',expected_eligible=3); mid=hashlib.sha256(db.read_bytes()).hexdigest(); b=M.export_taxonomy_families(db_path=db,output_dir=self.root/'out-b',expected_eligible=3); after=hashlib.sha256(db.read_bytes()).hexdigest()
        self.assertEqual(before,mid); self.assertEqual(mid,after); self.assertEqual(a['families_jsonl_sha256'],b['families_jsonl_sha256']); self.assertEqual(a['source_fingerprint_sha256'],b['source_fingerprint_sha256'])
        self.assertEqual((self.root/'out-a'/'families.jsonl').read_bytes(),(self.root/'out-b'/'families.jsonl').read_bytes())

    def test_family_evidence_covers_taxonomy_and_each_member(self):
        db=self.root/'f.db'; make_db(db,[row('CAND-001',1,'wares','merchandise.n.01'),row('CAND-002',2,'merchandise','merchandise.n.01')])
        f=M.map_taxonomy_families(M._read_rows(db),db_ref=str(db))['families'][0]; kinds=[x['kind'] for x in f['source']['evidence']]
        self.assertEqual(kinds.count('OBJECT_ATLAS_TAXONOMY'),1); self.assertEqual(kinds.count('OBJECT_ATLAS_RECORD'),2); self.assertEqual(len({x['evidence_id'] for x in f['source']['evidence']}),3)

    def test_noneligible_rows_are_not_members(self):
        db=self.root/'g.db'; make_db(db,[row('CAND-001',1,'wares','merchandise.n.01'),row('CAND-002',2,'merchandise','merchandise.n.01'),row('CAND-003',3,'goods','merchandise.n.01',status='rejected_suitability')])
        r=M.map_taxonomy_families(M._read_rows(db),db_ref=str(db)); self.assertEqual([m['member_id'] for m in r['families'][0]['members']],['CAND-001','CAND-002'])

    def test_missing_primary_synset_fails_closed(self):
        db=self.root/'h.db'; make_db(db,[('CAND-001',1,'book','[]','[]','physical_entity_path','none','eligible')])
        with self.assertRaisesRegex(M.TaxonomyFamilyMapError,'E_PRIMARY_SYNSET_MISSING'): M.map_taxonomy_families(M._read_rows(db),db_ref=str(db))

    def test_expected_eligible_count_mismatch_fails_closed(self):
        db=self.root/'i.db'; make_db(db,[row('CAND-001',1,'book','book.n.01')])
        with self.assertRaisesRegex(M.TaxonomyFamilyMapError,'E_ELIGIBLE_COUNT_MISMATCH'): M.export_taxonomy_families(db_path=db,output_dir=self.root/'out',expected_eligible=2)

    def test_live_sample_families_validate_against_h01_120(self):
        sample=json.loads((ROOT/'company'/'company-os'/'die-h01'/'fixtures'/'h01-121-taxonomy-family-map.sample.json').read_text())
        self.assertEqual(sample['schema'],'die.h01.taxonomy-family-map.sample.v1')
        self.assertEqual(len(sample['families']),4)
        for family in sample['families']:
            validate_semantic_family(family)
            self.assertEqual(family['family_class'],'TAXONOMIC')
            self.assertTrue(all(m['identity_effect']=='NONE' for m in family['members']))
            self.assertEqual(family['rights_class'],'REVIEW_REQUIRED')

    def test_semantic_key_slug_collision_fails_closed(self):
        rows=[{'id':'CAND-001','raw_noun_id':1,'canonical_name':'one','aliases':'[]','wordnet_synsets':'["foo\'s.n.01"]','suitability':'lexname=noun.artifact','ip_risk':'none','wave3_status':'eligible'},{'id':'CAND-002','raw_noun_id':2,'canonical_name':'two','aliases':'[]','wordnet_synsets':'["foo-s.n.01"]','suitability':'lexname=noun.artifact','ip_risk':'none','wave3_status':'eligible'}]
        with self.assertRaisesRegex(M.TaxonomyFamilyMapError,'E_SEMANTIC_KEY_COLLISION'):
            M.map_taxonomy_families(rows,db_ref='fixture.db')

    def test_synset_punctuation_is_slugged_but_preserved_in_evidence(self):
        db=self.root/'punct.db'; make_db(db,[row('CAND-001',1,"Adam's needle","adam's-needle.n.01"),row('CAND-002',2,'yucca',"adam's-needle.n.01")])
        f=M.map_taxonomy_families(M._read_rows(db),db_ref=str(db))['families'][0]
        self.assertEqual(f['semantic_identity']['semantic_key'],'wordnet.primary.adam-s-needle.n.01')
        self.assertIn("adam's-needle.n.01",f['semantic_identity']['definition'])
        self.assertIn("adam's-needle.n.01",f['source']['evidence'][0]['ref'])

    def test_family_ids_and_member_order_are_stable_under_source_row_order(self):
        raw=[{'id':'CAND-002','raw_noun_id':2,'canonical_name':'wares','aliases':'[]','wordnet_synsets':'["merchandise.n.01"]','suitability':'lexname=noun.artifact','ip_risk':'none','wave3_status':'eligible'},{'id':'CAND-001','raw_noun_id':1,'canonical_name':'merchandise','aliases':'[]','wordnet_synsets':'["merchandise.n.01"]','suitability':'lexname=noun.artifact','ip_risk':'none','wave3_status':'eligible'}]
        a=M.map_taxonomy_families(raw,db_ref='x.db')['families'][0]; b=M.map_taxonomy_families(list(reversed(raw)),db_ref='x.db')['families'][0]
        self.assertEqual(a['family_id'],b['family_id']); self.assertEqual([m['member_id'] for m in a['members']],['CAND-001','CAND-002'])

if __name__=='__main__': unittest.main()
