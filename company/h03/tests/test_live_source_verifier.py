import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'live_source_verifier.py'
spec=importlib.util.spec_from_file_location('live_source_verifier_test',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)


def resolver_public(host,port,type=None):
    return [(2,1,6,'',( '93.184.216.34', port ))]


def resolver_private(host,port,type=None):
    return [(2,1,6,'',( '127.0.0.1', port ))]


class LiveSourceVerifierTests(unittest.TestCase):
    def test_public_url_rejects_private_network(self):
        with self.assertRaisesRegex(ValueError,'PRIVATE_ADDRESS_FORBIDDEN'):
            mod.validate_public_url('https://example.com/path',resolver=resolver_private)

    def test_public_url_accepts_public_http_origin(self):
        self.assertEqual(mod.validate_public_url('https://example.com/path',resolver=resolver_public),'https://example.com/path')

    def test_public_url_rejects_userinfo_and_nonstandard_port(self):
        with self.assertRaisesRegex(ValueError,'USERINFO_FORBIDDEN'):
            mod.validate_public_url('https://u:p@example.com/',resolver=resolver_public)
        with self.assertRaisesRegex(ValueError,'PORT_FORBIDDEN'):
            mod.validate_public_url('https://example.com:8080/',resolver=resolver_public)

    def test_evidence_selection_prefers_relevance_then_restores_source_order(self):
        units=[
            {'evidence_id':'E1','text':'generic intro'},
            {'evidence_id':'E2','text':'pricing is 12 dollars per month'},
            {'evidence_id':'E3','text':'another pricing comparison'},
            {'evidence_id':'E4','text':'footer'},
        ]
        selected=mod._select_evidence_units(units,['pricing'],2)
        self.assertEqual([x['evidence_id'] for x in selected],['E2','E3'])

    def test_bundle_is_bounded_deduplicated_and_records_failures(self):
        calls=[]
        def fake_fetcher(**kwargs):
            calls.append(kwargs['url'])
            if 'bad.example' in kwargs['url']:
                raise RuntimeError('blocked')
            return {
                'source_id':kwargs['source_id'],'source_uri':kwargs['url'],'source_class':kwargs['source_class'],
                'rights_status':'GOVERNED_EXTERNAL','rights_policy':{'state':'REVIEWED_REFERENCE_ONLY'},
                'review':{'status':'ACCEPTED_FOR_KNOWLEDGE','crawler_or_llm_authority':False},
                'raw_sha256':'a'*64,'normalized_text_sha256':'b'*64,
                'evidence_units':[{'evidence_id':kwargs['source_id']+'-E1','text':'fact'}],
            }
        requests=[
            {'source_id':'S1','url':'https://good.example/a','source_class':'SPECIALIST_PUBLICATION','candidate_id':'C1'},
            {'source_id':'S2','url':'https://good.example/a','source_class':'SPECIALIST_PUBLICATION','candidate_id':'C1'},
            {'source_id':'S3','url':'https://bad.example/b','source_class':'COMPETITOR_PRODUCT','candidate_id':'C1'},
        ]
        out=mod.verify_source_bundle(run_id='R1',source_requests=requests,max_sources=3,fetcher=fake_fetcher)
        self.assertEqual(out['verified_count'],1)
        self.assertEqual(len(out['failures']),1)
        self.assertEqual(calls,['https://good.example/a','https://bad.example/b'])
        self.assertEqual(out['verified_sources'][0]['candidate_id'],'C1')


if __name__=='__main__':
    unittest.main()
