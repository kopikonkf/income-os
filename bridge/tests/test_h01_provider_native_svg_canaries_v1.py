from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / 'company/company-os/die-h01'
RECEIPT = H01 / 'receipts/H01-107-provider-native-svg-canaries.receipt.json'
RUNTIME = H01 / 'runtime/h01-provider-native-svg-canaries.v1.json'


def load(path: Path):
    return json.loads(path.read_text())


class ProviderNativeSvgCanariesTests(unittest.TestCase):
    def test_graph_done_and_final_provider_order(self):
        graph = load(H01 / 'die-h01-task-graph.v1.json')
        by = {row['id']: row for row in graph['tasks']}
        self.assertEqual(by['H01-107']['status'], 'DONE')
        self.assertEqual(by['H01-107']['depends_on'], ['H01-104A', 'H01-106', 'H01-025'])
        receipt = load(RECEIPT)
        self.assertEqual(receipt['status'], 'PASS')
        self.assertEqual(
            receipt['scope']['provider_order'],
            ['claude', 'chatgpt', 'qwen', 'gemini', 'grok', 'manus', 'copilot', 'duckai'],
        )
        self.assertEqual(receipt['scope']['native_svg_count'], 1)
        self.assertEqual(receipt['scope']['text_svg_count'], 5)
        self.assertEqual(receipt['scope']['unsupported_count'], 1)
        self.assertEqual(receipt['scope']['deferred_count'], 1)
        self.assertEqual(receipt['scope']['validated_svg_count'], 6)

    def test_all_final_canaries_reuse_p001_sequentially(self):
        receipt = load(RECEIPT)
        self.assertTrue(receipt['execution']['all_final_canaries_reused_p001'])
        for row in receipt['providers']:
            self.assertEqual(row['profile_id'], 'h01-web-p001')
            self.assertEqual(row['udd_id'], 'h01-web-s01')
            self.assertEqual(row['cdp_port'], 9201)
            self.assertTrue(row['browser_cleanup_pass'])
            self.assertFalse(row['provider_promoted'])
        self.assertTrue(receipt['acceptance']['all_browser_cleanup_pass'])

    def test_final_classification_matrix_is_honest(self):
        rows = {row['provider_id']: row for row in load(RECEIPT)['providers']}
        expected = {
            'claude': 'TEXT_SVG',
            'chatgpt': 'TEXT_SVG',
            'qwen': 'TEXT_SVG',
            'gemini': 'NATIVE_SVG',
            'grok': 'UNSUPPORTED',
            'manus': 'TEXT_SVG',
            'copilot': 'TEXT_SVG',
            'duckai': 'DEFERRED',
        }
        self.assertEqual({k: v['classification'] for k, v in rows.items()}, expected)
        self.assertEqual(rows['grok']['reason_code'], 'EMPTY_FINAL_RESPONSE')
        self.assertEqual(rows['duckai']['reason_code'], 'PROVIDER_TIMEOUT')
        self.assertEqual(rows['duckai']['model_surface_observed'], '5.6 Luna')
        self.assertEqual(rows['duckai']['reasoning_surface_observed'], 'Fast')

    def test_successful_provider_originals_match_receipts(self):
        receipt = load(RECEIPT)
        success = [r for r in receipt['providers'] if r['classification'] in {'TEXT_SVG', 'NATIVE_SVG'}]
        self.assertEqual(len(success), 6)
        for row in success:
            self.assertEqual(row['h01_103_status'], 'PASS')
            path = ROOT / row['provider_original_path']
            data = path.read_bytes()
            self.assertEqual(len(data), row['provider_original_bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), row['provider_original_sha256'])
            text = data.decode('utf-8')
            self.assertTrue(text.lstrip().startswith('<svg'))
            self.assertTrue(text.rstrip().endswith('</svg>'))

    def test_qwen_late_completion_and_gemini_native_file_are_preserved(self):
        rows = {row['provider_id']: row for row in load(RECEIPT)['providers']}
        self.assertTrue(rows['qwen']['late_completion_recheck'])
        self.assertEqual(rows['qwen']['classification'], 'TEXT_SVG')
        self.assertEqual(rows['qwen']['h01_104a_status'], 'SUCCEEDED')
        self.assertEqual(rows['gemini']['classification'], 'NATIVE_SVG')
        self.assertEqual(rows['gemini']['acquisition_method'], 'UI_DOWNLOAD_SVG')
        self.assertEqual(rows['gemini']['h01_104a_status'], 'NOT_APPLICABLE_NATIVE_FILE')
        self.assertEqual(rows['gemini']['provider_original_bytes'], 7987)

    def test_manus_limit_and_copilot_surface_are_recorded(self):
        rows = {row['provider_id']: row for row in load(RECEIPT)['providers']}
        self.assertEqual(rows['manus']['model_surface_observed'], 'Manus 1.6 Lite')
        self.assertEqual(rows['manus']['prompt_variant'], 'COMPACT_SEMANTIC_EQUIVALENT_UI_3000_CHAR_LIMIT')
        self.assertLessEqual(rows['manus']['prompt_chars'], 3000)
        self.assertEqual(rows['copilot']['model_surface_observed'], 'Smart')

    def test_superseded_wrong_profile_attempts_cannot_be_final_truth(self):
        receipt = load(RECEIPT)
        old = receipt['superseded_evidence']['wrong_profile_attempts']
        self.assertEqual(old, ['chatgpt-001', 'qwen-001', 'gemini-001', 'grok-001', 'manus-001', 'copilot-001'])
        self.assertTrue(all(row['profile_id'] == 'h01-web-p001' for row in receipt['providers']))

    def test_runtime_contract_and_safety(self):
        runtime = load(RUNTIME)
        self.assertEqual(runtime['status'], 'ACCEPTED')
        self.assertEqual(runtime['profile_policy']['profile_id'], 'h01-web-p001')
        self.assertTrue(runtime['profile_policy']['sequential_only'])
        self.assertEqual(runtime['native_file_acquisition']['provider'], 'gemini')
        self.assertTrue(runtime['native_file_acquisition']['h01_104a_text_extractor_not_falsely_claimed'])
        acceptance = load(RECEIPT)['acceptance']
        for key in ('cookies_or_tokens_read', 'session_bytes_read', 'browser_profile_copied', 'mission_control_mutated', 'provider_promotion_performed', 'submission_authorized', 'publication_authorized'):
            self.assertFalse(acceptance[key])


if __name__ == '__main__':
    unittest.main()
