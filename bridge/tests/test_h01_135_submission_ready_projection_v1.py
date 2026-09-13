import hashlib,json,sys,tempfile,unittest,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'company/company-os/die-h01/engineering/submission_ready_projection.py'
S=importlib.util.spec_from_file_location('h01_135_projection',LIB); M=importlib.util.module_from_spec(S); assert S and S.loader; sys.modules[S.name]=M; S.loader.exec_module(M)
def sha(b): return hashlib.sha256(b).hexdigest()
def make_pkg(root, *, sid='SEM-1', market='ADOBE', rights='PASS', qc='PASS', compat='COMPATIBLE', eligible=True):
    d=Path(root)/market.lower()/sid; f=d/'files'; f.mkdir(parents=True)
    data=b'<svg viewBox="0 0 10 10"></svg>\n'; (f/'asset.svg').write_bytes(data)
    meta=b'{"title":"x"}\n'; (f/'metadata.json').write_bytes(meta)
    m={'schema':'die.h01.marketplace-delivery-package.v1','marketplace':market,'semantic_asset_id':sid,'artifacts':[{'target':'asset.svg','sha256':sha(data)}],'sidecar_metadata':{'path':'files/metadata.json','sha256':sha(meta)},'compatibility':{'status':compat,'result':'PASS' if compat=='COMPATIBLE' else 'REVIEW_REQUIRED'},'rights_signal':{'result':rights},'founder_qc':qc,'submission_eligible':eligible}
    (d/'manifest.json').write_text(json.dumps(m,sort_keys=True,indent=2)+'\n'); return d
class ProjectionTests(unittest.TestCase):
    def test_only_fully_eligible_is_projected(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); src=r/'src'; out=r/'ready'; make_pkg(src,sid='GOOD'); make_pkg(src,sid='RIGHTS',rights='REVIEW_REQUIRED',eligible=False); make_pkg(src,sid='QC',qc='NOT_RECORDED',eligible=False)
            x=M.project_submission_ready(src,out); self.assertEqual(x['eligible_count'],1); self.assertTrue((out/'adobe/GOOD/asset.svg').is_file()); self.assertFalse((out/'adobe/RIGHTS').exists()); self.assertFalse((out/'adobe/QC').exists())
    def test_hash_bound_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); src=r/'src'; out=r/'ready'; make_pkg(src)
            a=M.project_submission_ready(src,out); snap1={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}; b=M.project_submission_ready(src,out); snap2={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}; self.assertEqual(snap1,snap2); self.assertEqual(a['index_file_sha256'],b['index_file_sha256'])
    def test_stale_projection_is_removed(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); src=r/'src'; out=r/'ready'; d=make_pkg(src); M.project_submission_ready(src,out); self.assertTrue((out/'adobe/SEM-1').exists()); m=json.loads((d/'manifest.json').read_text()); m['submission_eligible']=False; m['rights_signal']['result']='REVIEW_REQUIRED'; (d/'manifest.json').write_text(json.dumps(m)); M.project_submission_ready(src,out); self.assertFalse((out/'adobe/SEM-1').exists())
    def test_source_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); src=r/'src'; out=r/'ready'; d=make_pkg(src); (d/'files/asset.svg').write_bytes(b'tampered')
            with self.assertRaises(M.ProjectionError) as c: M.project_submission_ready(src,out)
            self.assertEqual(c.exception.code,'PACKAGE_HASH_MISMATCH')
    def test_unmanaged_nonempty_root_refused(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); src=r/'src'; out=r/'ready'; make_pkg(src); out.mkdir(); (out/'foreign.txt').write_text('x')
            with self.assertRaises(M.ProjectionError) as c: M.project_submission_ready(src,out)
            self.assertEqual(c.exception.code,'OUTPUT_ROOT_NOT_MANAGED')
if __name__=='__main__': unittest.main()
