"""FA-118 Duck.ai image-provider normalization from FA-W017 + Linux Cluster A evidence."""
from __future__ import annotations
from typing import Any

PROVIDER_ID='duckai'
TRANSPORT_CLASS='BROWSER_CDP'
BROWSER_RUNTIME_OWNER='MUXIA'
PROFILE_ID='chatgpt-linux-a'
BASE_URL='https://duck.ai/'
PRIMARY_ACQUISITION_ROUTE='INDEXEDDB_CHAT_IMAGES_BLOB'
FALLBACK_ACQUISITION_ROUTE='PROVIDER_DATA_URI_DOM'

def capability()->dict[str,Any]:
    return {
        'schema':'die.factory-asset.image-provider.v1','kind':'CAPABILITY','provider_id':PROVIDER_ID,
        'contract_version':'1.1.0','transport_classes':[TRANSPORT_CLASS],
        'browser_runtime_owner':BROWSER_RUNTIME_OWNER,'profile_id':PROFILE_ID,
        'image_generation':True,'output_formats':['JPEG','PNG','WEBP'],
        'auth_route':'NO_ACCOUNT_REQUIRED_OR_EXISTING_SESSION','capacity_state':'UNKNOWN',
    }

def browser_strategy()->dict[str,Any]:
    return {
        'schema':'die.factory-asset.browser-provider-strategy.v1','provider_id':PROVIDER_ID,
        'transport_class':TRANSPORT_CLASS,'browser_runtime_owner':BROWSER_RUNTIME_OWNER,
        'profile_id':PROFILE_ID,'base_url':BASE_URL,'mode_activation':['Tools','Create Image'],
        'submit_controls':['button[aria-label="Send"]','button[type="submit"]'],
        'composer_selector':'textarea[aria-label="Ask anything privately"], textarea',
        'primary_acquisition_route':PRIMARY_ACQUISITION_ROUTE,
        'fallback_acquisition_route':FALLBACK_ACQUISITION_ROUTE,
        'indexeddb_origin':'https://duck.ai','indexeddb_object_store':'chat-images',
        'minimum_image_dimensions':[512,512],'text_only_endpoint_eligible':False,
        'internal_chat_endpoint_is_success_contract':False,
        'credential_values_embedded':False,'session_material_embedded':False,
    }