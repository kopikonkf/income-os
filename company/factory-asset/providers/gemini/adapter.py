"""FA-114 clean Gemini provider contract normalized from FA-W013 evidence."""
from __future__ import annotations

from typing import Any

PROVIDER_ID = 'gemini'
TRANSPORT_CLASS = 'BROWSER_CDP'
BROWSER_RUNTIME_OWNER = 'MUXIA'
PROFILE_ID = 'chatgpt-linux-a'
BASE_URL = 'https://gemini.google.com/app'
ACQUISITION_ROUTE = 'PROVIDER_DOWNLOAD_CONTROL'

COMPOSER_SELECTORS = (
    '[contenteditable="true"][role="textbox"]',
    '.ql-editor[contenteditable="true"]',
    '[contenteditable="true"]',
    'textarea',
)
SIGN_IN_SELECTOR = 'a:has-text("Sign in"), button:has-text("Sign in"), [aria-label*="sign in" i]'
DOWNLOAD_SELECTOR = (
    'button[aria-label*="download" i], '
    '[role="button"][aria-label*="download" i], '
    'a[aria-label*="download" i], '
    'button[title*="download" i], '
    'a[title*="download" i], '
    'a[download]'
)


def capability() -> dict[str, Any]:
    return {
        'schema': 'die.factory-asset.image-provider.v1',
        'kind': 'CAPABILITY',
        'provider_id': PROVIDER_ID,
        'contract_version': '1.0.0',
        'transport_classes': [TRANSPORT_CLASS],
        'browser_runtime_owner': BROWSER_RUNTIME_OWNER,
        'profile_id': PROFILE_ID,
        'image_generation': True,
        'output_formats': ['JPEG', 'PNG', 'WEBP'],
        'capacity_state': 'UNKNOWN',
    }


def browser_strategy() -> dict[str, Any]:
    return {
        'schema': 'die.factory-asset.browser-provider-strategy.v1',
        'provider_id': PROVIDER_ID,
        'transport_class': TRANSPORT_CLASS,
        'browser_runtime_owner': BROWSER_RUNTIME_OWNER,
        'profile_id': PROFILE_ID,
        'base_url': BASE_URL,
        'composer_selectors': list(COMPOSER_SELECTORS),
        'auth_selector': SIGN_IN_SELECTOR,
        'download_selector': DOWNLOAD_SELECTOR,
        'acquisition_route': ACQUISITION_ROUTE,
        'generation_timeout_ms': 180000,
        'download_event_timeout_ms': 20000,
        'credential_values_embedded': False,
        'session_material_embedded': False,
    }


def normalize_canary_receipt(value: dict[str, Any]) -> dict[str, Any]:
    if value.get('provider_id') != PROVIDER_ID:
        raise ValueError('PROVIDER_MISMATCH')
    if value.get('transport_class') != TRANSPORT_CLASS:
        raise ValueError('TRANSPORT_MISMATCH')
    if value.get('status') != 'PASS':
        raise ValueError('CANARY_NOT_PASS')
    if value.get('operator_actions_after_dispatch') != 0:
        raise ValueError('POST_DISPATCH_OPERATOR_ACTION')
    if value.get('credential_values_read') is not False or value.get('cookies_or_tokens_read') is not False:
        raise ValueError('SECRET_BOUNDARY_VIOLATION')
    if not value.get('output_extracted_by_automation') or not value.get('prompt_submitted_by_automation'):
        raise ValueError('AUTOMATION_PROOF_INCOMPLETE')
    digest = value.get('sha256')
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError('SHA256_REQUIRED')
    return {
        'schema': 'die.factory-asset.image-provider.v1',
        'kind': 'GENERATE_RESULT',
        'provider_id': PROVIDER_ID,
        'transport_class': TRANSPORT_CLASS,
        'browser_runtime_owner': BROWSER_RUNTIME_OWNER,
        'profile_id': PROFILE_ID,
        'status': 'PASS',
        'sha256': digest,
        'bytes': int(value['bytes']),
        'mime': value['mime'],
        'local_path': value['local_path'],
        'original_byte_acquisition_method': value['original_byte_acquisition_method'],
        'operator_actions_after_dispatch': 0,
    }
