"""FA-116 clean Manus provider contract normalized from canonical FA-W015 evidence."""
from __future__ import annotations
from typing import Any

PROVIDER_ID='manus'; TRANSPORT_CLASS='BROWSER_CDP'; BROWSER_RUNTIME_OWNER='MUXIA'; PROFILE_ID='chatgpt-linux-a'
BASE_URL='https://manus.im/app'; ACQUISITION_ROUTE='GENERATED_MANUSCDN_RESPONSE_BODY'
EDITOR_SELECTOR='.tiptap.ProseMirror[contenteditable="true"]'

def capability()->dict[str,Any]:
    return {'schema':'die.factory-asset.image-provider.v1','kind':'CAPABILITY','provider_id':PROVIDER_ID,'contract_version':'1.0.0','transport_classes':[TRANSPORT_CLASS],'browser_runtime_owner':BROWSER_RUNTIME_OWNER,'profile_id':PROFILE_ID,'image_generation':True,'output_formats':['PNG','JPEG','WEBP'],'capacity_state':'UNKNOWN'}

def browser_strategy()->dict[str,Any]:
    return {'schema':'die.factory-asset.browser-provider-strategy.v1','provider_id':PROVIDER_ID,'transport_class':TRANSPORT_CLASS,'browser_runtime_owner':BROWSER_RUNTIME_OWNER,'profile_id':PROFILE_ID,'base_url':BASE_URL,'editor_selector':EDITOR_SELECTOR,'acquisition_route':ACQUISITION_ROUTE,'generated_host_rule':'*.manuscdn.com excluding files.manuscdn.com','deadline_ms':300000,'credential_values_embedded':False,'session_material_embedded':False,'guessed_api_endpoints':False}