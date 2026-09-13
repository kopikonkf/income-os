import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENG = ROOT / 'company' / 'company-os' / 'die-h01' / 'engineering'
sys.path.insert(0, str(ENG))
import provider_output_acquisition as A
import native_svg_request_contract as C

CASES = json.loads((ROOT / 'company/company-os/die-h01/fixtures/h01-104a/provider-output-cases.json').read_text())
REQ = json.loads((ROOT / 'company/company-os/die-h01/fixtures/h01-104/request.web-ai-adapter.json').read_text())


class ProviderOutputAcquisitionTests(unittest.TestCase):
    def test_plain_svg_extracts_exactly(self):
        svg, method = A.extract_single_svg(CASES['plain'])
        self.assertEqual(svg, CASES['plain'])
        self.assertEqual(method, 'ASSISTANT_DOM')

    def test_code_block_classified_without_markdown_bytes(self):
        svg, method = A.extract_single_svg(CASES['code_block'])
        self.assertTrue(svg.startswith('<svg'))
        self.assertNotIn('```', svg)
        self.assertEqual(method, 'CODE_BLOCK')

    def test_single_svg_inside_provider_prose_is_accepted(self):
        svg, method = A.extract_single_svg(CASES['prose_wrapped'])
        self.assertTrue(svg.startswith('<svg'))
        self.assertTrue(svg.endswith('</svg>'))
        self.assertEqual(method, 'ASSISTANT_DOM')

    def test_ambiguous_multiple_svg_fails_closed(self):
        with self.assertRaisesRegex(A.ProviderOutputError, 'AMBIGUOUS_PROVIDER_OUTPUT'):
            A.extract_single_svg(CASES['ambiguous'])

    def test_forbidden_svg_feature_fails_closed(self):
        with self.assertRaisesRegex(A.ProviderOutputError, 'SVG_FORBIDDEN_FEATURE'):
            A.extract_single_svg(CASES['forbidden'])

    def test_missing_dimensions_fails_closed(self):
        with self.assertRaisesRegex(A.ProviderOutputError, 'SVG_DIMENSIONS_MISSING'):
            A.extract_single_svg(CASES['missing_dimensions'])

    def test_empty_and_non_svg_fail_closed(self):
        for value in ('', 'plain text only'):
            with self.assertRaises(A.ProviderOutputError):
                A.extract_single_svg(value)

    def test_acquisition_persists_immutable_original_and_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            receipt, state = A.acquire_svg_text(
                job_id='H01-104A-CANARY-001', request_id=REQ['request_id'], provider_id='claude',
                profile_id='h01-web-p001', provider_status='COMPLETED', provider_response_text=CASES['prose_wrapped'],
                output_dir=td, completion_signal='PROVIDER_STABLE_FINAL', completed_at='2026-09-12T14:00:00Z', finish_reason='STOP')
            artifact = Path(td) / 'provider-original.svg'
            self.assertTrue(artifact.exists())
            self.assertEqual(A.sha256_bytes(artifact.read_bytes()), receipt['artifact']['sha256'])
            self.assertFalse(any(receipt['safety'].values()))
            A.validate_receipt(receipt)
            self.assertEqual(state, 'CREATED/CREATED/CREATED')
            _, state2 = A.acquire_svg_text(
                job_id='H01-104A-CANARY-001', request_id=REQ['request_id'], provider_id='claude',
                profile_id='h01-web-p001', provider_status='COMPLETED', provider_response_text=CASES['prose_wrapped'],
                output_dir=td, completion_signal='PROVIDER_STABLE_FINAL', completed_at='2026-09-12T14:00:00Z', finish_reason='STOP')
            self.assertEqual(state2, 'UNCHANGED/UNCHANGED/UNCHANGED')

    def test_geometry_fragment_is_normalized_without_provider_reprompt(self):
        fragment = '<g><polygon points="10,10 90,10 90,90 10,90" fill="#c1cbdaf0"/><path d="M 20 20 L 80 80 Z" fill="#334455"/></g>'
        surface = A.extract_svg_surface(fragment)
        self.assertEqual(surface['source_kind'], 'SVG_GEOMETRY_FRAGMENT')
        self.assertTrue(surface['candidate_svg'].startswith('<svg'))
        self.assertIn('viewBox=', surface['candidate_svg'])
        self.assertNotIn('#c1cbdaf0', surface['candidate_svg'])
        self.assertEqual(surface['normalization']['provider_reprompted'], False)
        self.assertEqual(surface['normalization']['geometry_preserved'], True)
        self.assertEqual(surface['normalization']['geometry_tag_count'], 2)
        self.assertEqual(surface['normalization']['alpha_hex_normalizations'], 1)

    def test_conflicting_provider_original_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            A.acquire_svg_text(job_id='j', request_id='r', provider_id='qwen', profile_id='p', provider_status='COMPLETED',
                provider_response_text=CASES['plain'], output_dir=td, completion_signal='FINAL', completed_at='2026-09-12T14:00:00Z')
            with self.assertRaisesRegex(A.ProviderOutputError, 'ARTIFACT_CONFLICT'):
                A.acquire_svg_text(job_id='j', request_id='r', provider_id='qwen', profile_id='p', provider_status='COMPLETED',
                    provider_response_text=CASES['code_block'], output_dir=td, completion_signal='FINAL', completed_at='2026-09-12T14:00:00Z')

    def test_h01_104_receipt_preserves_raw_response_and_extracted_candidate_hashes(self):
        svg, _ = A.extract_single_svg(CASES['prose_wrapped'])
        r = C.build_success_receipt(
            request=REQ, ingress='WEB_AI_ADAPTER', dispatch_commit_id='dispatch-h01-104a', provider_status='COMPLETED',
            provider_response_text=CASES['prose_wrapped'], candidate_svg_text=svg,
            h01_103_canonical_svg_sha256='a'*64, provider_request_id='provider-104a', finish_reason='STOP')
        self.assertEqual(r['provider_result']['provider_response_sha256'], A.sha256_text(CASES['prose_wrapped']))
        self.assertEqual(r['provider_result']['candidate_svg_sha256'], A.sha256_text(svg))

    def test_h01_104_accepts_deterministic_transport_normalization_lineage(self):
        fragment = '<g><polygon points="10,10 90,10 90,90 10,90" fill="#c1cbdaf0"/></g>'
        surface = A.extract_svg_surface(fragment)
        r = C.build_success_receipt(
            request=REQ, ingress='WEB_AI_ADAPTER', dispatch_commit_id='dispatch-normalized', provider_status='COMPLETED',
            provider_response_text=fragment, candidate_svg_text=surface['candidate_svg'], transport_normalization=surface['normalization'],
            h01_103_canonical_svg_sha256='b'*64, finish_reason='PROVIDER_UI_TERMINAL')
        self.assertEqual(r['provider_result']['provider_response_sha256'], A.sha256_text(fragment))
        self.assertEqual(r['provider_result']['candidate_svg_sha256'], A.sha256_text(surface['candidate_svg']))
        self.assertEqual(r['transport_normalization']['method'], 'SVG_GEOMETRY_FRAGMENT_ENVELOPE_V1')
        self.assertFalse(r['transport_normalization']['provider_reprompted'])

    def test_h01_104_candidate_must_be_from_provider_response(self):
        with self.assertRaisesRegex(C.NativeSvgContractError, 'CANDIDATE_NOT_IN_PROVIDER_RESPONSE'):
            C.build_success_receipt(
                request=REQ, ingress='WEB_AI_ADAPTER', dispatch_commit_id='dispatch-h01-104a', provider_status='COMPLETED',
                provider_response_text=CASES['plain'], candidate_svg_text=CASES['code_block'].split('\n',1)[1].rsplit('\n',1)[0],
                h01_103_canonical_svg_sha256='a'*64)


if __name__ == '__main__':
    unittest.main()
