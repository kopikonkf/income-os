from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ExecutionMode = Literal["AUTOMATED_ALLOWED", "OPERATOR_REQUIRED", "OFFICIAL_API_ONLY", "BLOCKED_POLICY_UNKNOWN"]
Operation = Literal["prepare", "submit", "reconcile", "receipt"]

@dataclass(frozen=True)
class SubmissionAdapterContract:
    platform: str
    adapter_version: str
    execution_mode: ExecutionMode
    policy_profile_sha256: str
    prepare_supported: bool = True
    submit_supported: bool = False
    reconcile_supported: bool = True
    receipt_supported: bool = True

    def capability(self, operation: Operation) -> dict[str, object]:
        supported = {
            "prepare": self.prepare_supported,
            "submit": self.submit_supported,
            "reconcile": self.reconcile_supported,
            "receipt": self.receipt_supported,
        }[operation]
        external_action = operation == "submit"
        if self.execution_mode == "BLOCKED_POLICY_UNKNOWN" and external_action:
            supported = False
        if self.execution_mode == "OPERATOR_REQUIRED" and external_action:
            supported = False
        return {
            "operation": operation,
            "supported_by_adapter": supported,
            "external_action": external_action,
            "execution_mode": self.execution_mode,
            "requires_founder_authority": external_action,
            "requires_external_credentials": external_action,
            "policy_profile_sha256": self.policy_profile_sha256,
        }

    def assert_submit_path(self, *, founder_authorized: bool, official_api: bool) -> None:
        if self.execution_mode == "BLOCKED_POLICY_UNKNOWN":
            raise PermissionError("platform policy unknown; submission blocked")
        if self.execution_mode == "OPERATOR_REQUIRED":
            raise PermissionError("operator handoff required; adapter may not submit")
        if self.execution_mode == "OFFICIAL_API_ONLY" and not official_api:
            raise PermissionError("official API required by execution policy")
        if not self.submit_supported:
            raise PermissionError("adapter submit capability is not implemented")
        if not founder_authorized:
            raise PermissionError("explicit Founder submission authority required")
