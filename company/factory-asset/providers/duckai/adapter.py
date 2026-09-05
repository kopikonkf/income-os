"""FA-118 clean Duck.ai image route normalized from canonical FA-W017 evidence."""
from __future__ import annotations
from typing import Any
PROVIDER_ID='duckai'; TRANSPORT_CLASS='BROWSER_CDP'; BROWSER_RUNTIME_OWNER='MUXIA'; PROFILE_ID='chatgpt-linux-a'; BASE_URL='https://duck.ai/'; ACQUISITION_ROUTE='PROVIDER_DATA_URI_DOM'

def capability()->dict[str,Any]:
    return {'schema':'die.factory-asset.image-provider.v1','kind':'CAPABILITY','provider_id':PROVIDER_ID,'contract_version':'1.0.0','transport_classes':[TRANSPORT_CLASS],'browser_runtime_owner':BROWSER_RUNTIME_OWNER,'profile_id':PROFILE_ID,'image_generation':True,'output_formats':['JPEG','PNG','WEBP'],'auth_route':'NO_ACCOUNT_REQUIRED_OR_EXISTING_SESSION','capacity_state':'UNKNOWN'}

def browser_strategy()->dict[str,Any]:
    return {'schema':'die.factory-asset.browser-provider-strategy.v1','provider_id':PROVIDER_ID,'transport_class':TRANSPORT_CLASS,'browser_runtime_owner':BROWSER_RUNTIME_OWNER,'profile_id':PROFILE_ID,'base_url':BASE_URL,'mode_activation':['Tools','Create Image'],'submit_label':'Create','composer_selector':'textarea[aria-label="Ask anything privately"], textarea','acquisition_route':ACQUISITION_ROUTE,'deadline_ms':180000,'text_only_endpoint_eligible':False,'credential_values_embedded':False,'session_material_embedded':False}