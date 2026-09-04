from __future__ import annotations
from copy import deepcopy
from typing import Any


def build_provider_dashboard(*, policy_registry:dict[str,Any], fixture:dict[str,Any], capacity_ledger_cls, evaluate_policy, route_provider, observability, today:str, now:str, route_asset_type:str="PHOTO") -> dict[str,Any]:
    ledger=capacity_ledger_cls()
    for event in fixture["capacity_events"]:
        ledger.record(event)
    policy_by_profile={row["profile_id"]:row for row in policy_registry["profiles"]}
    capacity_by_profile={profile_id:ledger.snapshot(profile_id,now=now,max_age_seconds=86400) for profile_id in policy_by_profile}
    candidates=[]
    rows=[]
    for base in fixture["routing_profiles"]:
        policy=policy_by_profile[base["profile_id"]]
        policy_result=evaluate_policy(policy,today=today)
        cap=capacity_by_profile[base["profile_id"]]
        candidate=deepcopy(base)
        candidate["policy_allowed"]=bool(policy_result["allowed"])
        candidate["capacity_state"]=cap.state
        candidates.append(candidate)
        if policy["policy_state"]=="DEFERRED_PLATFORM_GATE": eligibility="DEFERRED_OPTIONAL"
        elif not policy_result["allowed"]: eligibility="BLOCKED"
        else: eligibility="ELIGIBLE"
        if not policy_result["allowed"]: health="POLICY_BLOCKED"
        elif cap.state=="AVAILABLE": health="READY"
        elif cap.state=="CONSTRAINED": health="DEGRADED"
        elif cap.state=="UNAVAILABLE": health="UNAVAILABLE"
        else: health="UNKNOWN"
        rows.append({
            "provider_id":base["provider_id"],"profile_id":base["profile_id"],"eligibility":eligibility,
            "health":health,"capacity":cap.state,"policy":policy_result["code"],"transport":policy["automation_route"],
            "last_evidence":cap.observed_at,"evidence_ref":cap.evidence_ref,
            "routing_reason":"PENDING_ROUTER_EVALUATION","retry_after_seconds":cap.retry_after_seconds,
        })
    try:
        decision=route_provider(asset_type=route_asset_type,candidates=candidates)
        selected=decision.profile_id
        rejected={x["profile_id"]:x["reasons"] for x in decision.rejected}
    except Exception as exc:
        selected=None
        rejected={getattr(x,"profile_id",str(i)):[] for i,x in enumerate([])}
        if getattr(exc,"code",None)!="NO_ELIGIBLE_PROVIDER": raise
        rejected={x["profile_id"]:x["reasons"] for x in exc.reasons}
    for row in rows:
        if row["profile_id"]==selected: row["routing_reason"]="SELECTED_DETERMINISTIC_ROUTE"
        elif row["profile_id"] in rejected: row["routing_reason"]="REJECTED:"+",".join(rejected[row["profile_id"]])
        else: row["routing_reason"]="ELIGIBLE_NOT_SELECTED_BY_RANK"
    result={
        "schema":"die.factory-asset.provider-dashboard.v1","evidence_mode":fixture["evidence_mode"],
        "observed_at":fixture["observed_at"],"route_asset_type":route_asset_type,"selected_profile_id":selected,
        "providers":rows,"guessed_quota_present":False,"provider_dispatch_performed":False,
    }
    observability.assert_secret_free(result)
    return result