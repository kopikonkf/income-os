from __future__ import annotations

from typing import Any

FORBIDDEN_PROFILE_CLASSES={
    'MISSION_CONTROL_PRINCIPAL_PRIMARY',
    'MISSION_CONTROL_ARCHITECT_PRIMARY',
    'DIVISION01_PRIMARY',
    'OTHER_HOLDING_OPERATIONAL',
}
ALLOWED_PURPOSES={'KNOWLEDGE_WORKFORCE','GROWTH_WORKFORCE','COMMERCE_OPERATOR'}


def validate_operational_binding(binding:dict[str,Any])->dict[str,Any]:
    if not isinstance(binding,dict) or binding.get('schema_version')!='die.h03.operational-browser-binding.v1' or binding.get('holding_id')!='H03':
        raise ValueError('H03_BROWSER_BINDING_SCHEMA_INVALID')
    if binding.get('pool_owner')!='H03':
        raise ValueError('H03_BROWSER_POOL_OWNER_INVALID')
    if binding.get('purpose') not in ALLOWED_PURPOSES:
        raise ValueError('H03_BROWSER_PURPOSE_INVALID')
    profile_class=binding.get('profile_class')
    if profile_class in FORBIDDEN_PROFILE_CLASSES:
        raise ValueError(f'H03_BROWSER_CROSS_BOUNDARY_PROFILE_FORBIDDEN:{profile_class}')
    if profile_class!='H03_DEDICATED_OPERATIONAL':
        raise ValueError('H03_BROWSER_DEDICATED_PROFILE_REQUIRED')
    if binding.get('session_material_policy')!='HOST_LOCAL_NOT_PRODUCT_TRUTH':
        raise ValueError('H03_BROWSER_SESSION_POLICY_INVALID')
    if binding.get('transport_family')!='BROWSER_CDP':
        raise ValueError('H03_BROWSER_INITIAL_TRANSPORT_INVALID')
    for forbidden in ('profile_path','user_data_dir','cookies','cookie','tokens','access_token','refresh_token','credentials','session_bytes'):
        if forbidden in binding:
            raise ValueError(f'H03_BROWSER_SECRET_OR_PATH_FORBIDDEN:{forbidden}')
    return binding


def invalidate_foreign_preflight(*, source_profile_class:str, observation_ref:str)->dict[str,Any]:
    if source_profile_class not in FORBIDDEN_PROFILE_CLASSES:
        raise ValueError('H03_BROWSER_INVALIDATION_REQUIRES_FOREIGN_PROFILE')
    return {
        'schema_version':'die.h03.browser-preflight-invalidation.v1',
        'holding_id':'H03',
        'observation_ref':observation_ref,
        'source_profile_class':source_profile_class,
        'valid_for_h03_runtime_readiness':False,
        'reason':'Cross-control-plane browser profile reuse is forbidden; operational readiness must be re-probed using an H03-dedicated profile pool.',
    }
