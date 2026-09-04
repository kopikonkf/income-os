from __future__ import annotations
import hashlib,json
from typing import Any

class MotionCapabilityError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

ALLOWED_TEMPORAL_VERBS={'fill','settle','open','close','assemble','transform','progress','load','process','complete','transition','reveal','expand','collapse','rotate','flow','pulse','count','move'}
VALUE_KINDS={'STATE_CHANGE','PROCESS','TRANSFORMATION','FEEDBACK','SEQUENCE','ATTENTION_GUIDANCE'}

def _sha(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def evaluate_motion_capability(candidate:dict[str,Any])->dict[str,Any]:
    required=('seed_noun','product_expression','buyer_utility','evidence_state','meaningful_visual_change','motion_value_kind','temporal_verbs')
    missing=[k for k in required if k not in candidate]
    if missing: raise MotionCapabilityError('CANDIDATE_FIELDS_MISSING',','.join(missing))
    if candidate['evidence_state'] not in {'COMPLETE','PARTIAL','NONE'}: raise MotionCapabilityError('EVIDENCE_STATE_INVALID',str(candidate['evidence_state']))
    if not isinstance(candidate['temporal_verbs'],list) or any(not isinstance(v,str) for v in candidate['temporal_verbs']): raise MotionCapabilityError('TEMPORAL_VERBS_INVALID','list[str] required')
    verbs=[v.strip().casefold() for v in candidate['temporal_verbs'] if v.strip()]
    reasons=[]
    if candidate.get('commercial_relevance')=='REJECTED':
        outcome='REJECT';reasons.append('COMMERCIAL_RELEVANCE_REJECTED')
    elif candidate['evidence_state']!='COMPLETE' or candidate['meaningful_visual_change'] is None or not candidate['buyer_utility']:
        outcome='RESEARCH';reasons.append('MOTION_EVIDENCE_INCOMPLETE')
    elif not verbs or candidate['meaningful_visual_change'] is False:
        outcome='STATIC_ONLY';reasons.append('NO_MEANINGFUL_TEMPORAL_CHANGE')
    elif candidate['motion_value_kind'] not in VALUE_KINDS:
        outcome='STATIC_ONLY';reasons.append('TEMPORAL_CHANGE_LACKS_BUYER_VALUE')
    elif any(v not in ALLOWED_TEMPORAL_VERBS for v in verbs):
        outcome='RESEARCH';reasons.append('UNMODELED_TEMPORAL_VERB')
    elif candidate.get('static_equivalent_sufficient') is True:
        outcome='STATIC_ONLY';reasons.append('STATIC_EQUIVALENT_COMMUNICATES_SAME_VALUE')
    else:
        outcome='MOTION_ELIGIBLE';reasons.extend(['MEANINGFUL_VISUAL_CHANGE','TEMPORAL_BUYER_VALUE_SUPPORTED'])
    result={'schema':'die.factory-asset.motion-capability.v1','result':outcome,'seed_noun':candidate['seed_noun'],'product_expression':candidate['product_expression'],'temporal_verbs':verbs,'buyer_utility':candidate['buyer_utility'],'motion_value_kind':candidate['motion_value_kind'],'meaningful_visual_change':candidate['meaningful_visual_change'],'static_equivalent_sufficient':candidate.get('static_equivalent_sufficient'),'reasons':reasons,'motion_production_authorized':outcome=='MOTION_ELIGIBLE','automatic_animation_of_static_asset':False}
    result['decision_sha256']=_sha(result);return result