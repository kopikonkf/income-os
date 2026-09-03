from __future__ import annotations
from typing import Any

def queue_event(job:dict[str,Any])->dict[str,Any]:
    return {'schema':'die.factory-asset.console-api.v1','kind':'QUEUE_EVENT','job_id':job['job_id'],'state':job['state'],'attempts':job['attempts'],'retries':job['retries'],'recovery_count':job['recovery_count'],'provider_id':job.get('intent',{}).get('provider_id'),'failure_code':job.get('failure_code'),'artifact_sha256':job.get('artifact_sha256'),'blueprint_id':job.get('intent',{}).get('blueprint_id',''),'semantic_asset_id':job.get('intent',{}).get('semantic_asset_id',''),'label':job.get('intent',{}).get('label','')}

def provider_event(*,provider_id:str,profile_id:str,eligibility:str,capacity:str,policy:str,routing_reason:str)->dict[str,Any]:
    return {'schema':'die.factory-asset.console-api.v1','kind':'PROVIDER_EVENT','provider_id':provider_id,'profile_id':profile_id,'eligibility':eligibility,'capacity':capacity,'policy':policy,'routing_reason':routing_reason}

def job_intent(*,job_id:str,idempotency_key:str,blueprint_id:str,semantic_asset_id:str,label:str)->dict[str,Any]:
    return {'schema':'die.factory-asset.console-api.v1','kind':'JOB_INTENT','job_id':job_id,'idempotency_key':idempotency_key,'blueprint_id':blueprint_id,'semantic_asset_id':semantic_asset_id,'label':label}