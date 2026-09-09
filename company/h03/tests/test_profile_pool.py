import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'profile_pool.py'
spec=importlib.util.spec_from_file_location('profile_pool',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
REG=json.loads((ROOT/'company'/'h03'/'runtime'/'provider-worker-registry.v1.json').read_text(encoding='utf-8'))

class ProfilePoolTests(unittest.TestCase):
    def pool(self):
        return {'schema_version':mod.SCHEMA,'holding_id':'H03','pool_id':'knowledge-pool','purpose':'KNOWLEDGE_WORKFORCE','session_material_policy':'HOST_LOCAL_NOT_PRODUCT_TRUTH','shards':[{'shard_id':'knowledge-a','state':'READY','providers':[{'provider_id':'qwen','state':'READY','available_slots':1,'transport_family':'SESSION_API'},{'provider_id':'gemini','state':'READY','available_slots':1,'transport_family':'BROWSER_CDP'}]}]}
    def test_single_multi_provider_shard_is_valid(self):
        pool=mod.validate_profile_pool(self.pool()); self.assertEqual(len(pool['shards']),1); self.assertEqual(len(pool['shards'][0]['providers']),2)
    def test_profile_path_or_secret_material_forbidden(self):
        for key in ('profile_path','cookies','access_token'):
            p=self.pool(); p['shards'][0][key]='secret-or-path'
            with self.assertRaisesRegex(ValueError,'PROFILE_POOL_SECRET_OR_PATH_FORBIDDEN'):
                mod.validate_profile_pool(p)
    def test_router_uses_initial_shard_then_alternate_shard(self):
        p=self.pool(); pick=mod.route_worker_from_pool(role='KNOWLEDGE_RESEARCHER',registry=REG,pool=p,required_capabilities=['web_research']); self.assertEqual(pick['provider_id'],'qwen'); self.assertEqual(pick['profile_shard_id'],'knowledge-a')
        p['shards'][0]['state']='UNAVAILABLE'
        p['shards'].append({'shard_id':'knowledge-b','state':'READY','providers':[{'provider_id':'qwen','state':'UNAVAILABLE','available_slots':0,'transport_family':'SESSION_API'},{'provider_id':'gemini','state':'READY','available_slots':2,'transport_family':'BROWSER_CDP'}]})
        pick=mod.route_worker_from_pool(role='KNOWLEDGE_RESEARCHER',registry=REG,pool=p,required_capabilities=['web_research']); self.assertEqual(pick['provider_id'],'gemini'); self.assertEqual(pick['profile_shard_id'],'knowledge-b')
    def test_unavailable_all_shards_is_typed_no_slot(self):
        p=self.pool(); p['shards'][0]['state']='UNAVAILABLE'
        with self.assertRaisesRegex(RuntimeError,'NO_ELIGIBLE_WORKER_SLOT'):
            mod.route_worker_from_pool(role='PRODUCER',registry=REG,pool=p,required_capabilities=['text_generation'])
