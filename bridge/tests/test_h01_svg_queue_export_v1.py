import hashlib, importlib.util, json, sqlite3, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('h01q',ROOT/'bin/die_h01_svg_queue.py')
M=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=M; SPEC.loader.exec_module(M)

def h(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def make_db(path,rows):
    con=sqlite3.connect(path)
    con.execute('''create table candidate_seeds(id text primary key,raw_noun_id integer not null,canonical_name text not null,
                 source_tier text,suitability text,ip_risk text,wave3_status text)''')
    con.executemany('insert into candidate_seeds values(?,?,?,?,?,?,?)',rows); con.commit(); con.close()

class QueueExportTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.root=Path(self.t.name); self.db=self.root/'atlas.db'; self.out=self.root/'queue'
        self.rows=[
            ('CAND-0000003',3,'hammer','review','lexname=noun.artifact','none','eligible'),
            ('CAND-0000001',1,'book','pass','physical_entity_path','none','eligible'),
            ('CAND-0000002',2,'cat','pass','lexname=noun.animal','none','eligible'),
        ]
        make_db(self.db,self.rows); self.old=M.EXPECTED_COUNT; M.EXPECTED_COUNT=3
    def tearDown(self): M.EXPECTED_COUNT=self.old; self.t.cleanup()
    def test_export_is_stable_ordered_and_idempotent(self):
        before=h(self.db); s1,m1=M.export(self.db,self.out); after=h(self.db)
        self.assertEqual((s1,before,after),('CREATED',before,before))
        lines=[json.loads(x) for x in (self.out/'queue.jsonl').read_text().splitlines()]
        self.assertEqual([x['source']['raw_noun_id'] for x in lines],[1,2,3])
        self.assertEqual([x['queue_position'] for x in lines],[1,2,3])
        self.assertEqual(lines[0]['queue_item_id'],'H01-SVGQ-CAND-0000001')
        self.assertTrue(all(x['dispatch_eligible'] for x in lines))
        qh=h(self.out/'queue.jsonl'); mh=h(self.out/'manifest.json')
        s2,m2=M.export(self.db,self.out)
        self.assertEqual(s2,'UNCHANGED'); self.assertEqual(h(self.out/'queue.jsonl'),qh); self.assertEqual(h(self.out/'manifest.json'),mh); self.assertEqual(m1,m2)
    def test_source_review_tier_does_not_override_wave3_eligibility(self):
        _,_,m=M.build(self.db)
        self.assertEqual(m['rights_gate_counts'],{'PASS':3}); self.assertEqual(m['feasibility_gate_counts'],{'PASS':3}); self.assertEqual(m['dispatch_eligible_count'],3)
    def test_existing_conflict_fails_closed(self):
        M.export(self.db,self.out); (self.out/'queue.jsonl').write_text('tampered\n')
        with self.assertRaisesRegex(M.QueueExportError,'E_EXISTING_QUEUE_CONFLICT'): M.export(self.db,self.out)
    def test_source_count_drift_fails_closed(self):
        M.EXPECTED_COUNT=4
        with self.assertRaisesRegex(M.QueueExportError,'E_SOURCE_COUNT'): M.build(self.db)
    def test_duplicate_normalized_name_fails_closed(self):
        db=self.root/'dup.db'; make_db(db,[('CAND-1',1,'Book','pass','physical_entity_path','none','eligible'),('CAND-2',2,' book ','pass','physical_entity_path','none','eligible')]); M.EXPECTED_COUNT=2
        with self.assertRaisesRegex(M.QueueExportError,'E_CANONICAL_NAME_IDENTITY'): M.build(db)
    def test_noneligible_rows_are_not_exported(self):
        db=self.root/'mix.db'; make_db(db,[('CAND-1',1,'book','pass','physical_entity_path','none','eligible'),('CAND-2',2,'city','pass','lexname=noun.location','none','rejected_suitability')]); M.EXPECTED_COUNT=1
        q,_,m=M.build(db); rows=[json.loads(x) for x in q.decode().splitlines()]
        self.assertEqual([x['source']['canonical_name'] for x in rows],['book']); self.assertEqual(m['queue_row_count'],1)

if __name__=='__main__': unittest.main()
