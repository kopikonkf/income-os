import importlib.util,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('mi',R/'company/factory-asset/lib/master_ingestion.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def test_duplicate_bytes_reuse_one_blob_but_keep_attempt_receipts(tmp_path):
 a=tmp_path/'a.png';b=tmp_path/'b.png';a.write_bytes(b'same-master-bytes');b.write_bytes(b'same-master-bytes');root=tmp_path/'stage'
 r1=m.stage_master(source_path=a,staging_root=root,attempt_id='attempt-001',semantic_asset_id='FASA-INGEST_001',blueprint_id='FABP-INGEST_001');r2=m.stage_master(source_path=b,staging_root=root,attempt_id='attempt-002',semantic_asset_id='FASA-INGEST_001',blueprint_id='FABP-INGEST_001');idx=m.staged_index(root)
 assert r1['staged_blob_path']==r2['staged_blob_path'];assert r1['blob_reused'] is False and r2['blob_reused'] is True;assert idx['attempt_count']==2 and idx['unique_blob_count']==1
def test_staging_never_claims_canonical_truth(tmp_path):
 p=tmp_path/'m.bin';p.write_bytes(b'x');r=m.stage_master(source_path=p,staging_root=tmp_path/'s',attempt_id='a1',semantic_asset_id='FASA-INGEST_001',blueprint_id='FABP-INGEST_001');assert r['canonical_truth'] is False;assert r['ingestion_state']=='STAGED_NOT_CANONICAL';assert r['state_manager_commit_required'] is True;assert r['state_manager_proposal']['physical_writer_required']=='DIE_STATE_MANAGER'
def test_expected_hash_mismatch_rejected(tmp_path):
 p=tmp_path/'m.bin';p.write_bytes(b'x')
 with pytest.raises(m.MasterIngestionError) as e:m.stage_master(source_path=p,staging_root=tmp_path/'s',attempt_id='a1',semantic_asset_id='FASA-INGEST_001',blueprint_id='FABP-INGEST_001',expected_sha256='a'*64)
 assert e.value.code=='SOURCE_HASH_MISMATCH'
def test_attempt_id_conflict_rejected(tmp_path):
 a=tmp_path/'a';b=tmp_path/'b';a.write_bytes(b'a');b.write_bytes(b'b');root=tmp_path/'s';m.stage_master(source_path=a,staging_root=root,attempt_id='a1',semantic_asset_id='FASA-INGEST_001',blueprint_id='FABP-INGEST_001')
 with pytest.raises(m.MasterIngestionError) as e:m.stage_master(source_path=b,staging_root=root,attempt_id='a1',semantic_asset_id='FASA-INGEST_001',blueprint_id='FABP-INGEST_001')
 assert e.value.code=='ATTEMPT_ID_CONFLICT'
def test_hash_address_collision_fails_closed(tmp_path,monkeypatch):
 p=tmp_path/'m';p.write_bytes(b'abc');root=tmp_path/'s';r=m.stage_master(source_path=p,staging_root=root,attempt_id='a1',semantic_asset_id='FASA-INGEST_001',blueprint_id='FABP-INGEST_001');Path(r['staged_blob_path']).write_bytes(b'corrupt')
 with pytest.raises(m.MasterIngestionError) as e:m.stage_master(source_path=p,staging_root=root,attempt_id='a2',semantic_asset_id='FASA-INGEST_001',blueprint_id='FABP-INGEST_001')
 assert e.value.code=='CONTENT_ADDRESS_COLLISION'