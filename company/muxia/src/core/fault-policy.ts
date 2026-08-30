export const FAULT_KINDS = [
  'TIMEOUT',
  'BROWSER_CRASH',
  'LEASE_CONTENTION',
  'DISK_ARTIFACT_FAILURE',
  'AUTH_REQUIRED',
] as const;

export type FaultKind = (typeof FAULT_KINDS)[number];

export interface FaultDisposition {
  fault: FaultKind;
  jobState: 'TIMED_OUT' | 'FAILED' | 'BLOCKED' | 'WAITING_OPERATOR';
  profileState: 'READY' | 'UNCHANGED' | 'AUTH_REQUIRED';
  recovery: string;
  escalation: string;
  successAllowed: false;
}

const FAULT_DISPOSITIONS: Readonly<Record<FaultKind, FaultDisposition>> = {
  TIMEOUT: {
    fault: 'TIMEOUT',
    jobState: 'TIMED_OUT',
    profileState: 'READY',
    recovery: 'RELEASE_LEASE_THEN_BOUNDED_REQUEUE',
    escalation: 'OPERATOR_AFTER_RETRY_LIMIT',
    successAllowed: false,
  },
  BROWSER_CRASH: {
    fault: 'BROWSER_CRASH',
    jobState: 'FAILED',
    profileState: 'READY',
    recovery: 'CRASH_RECOVERY_RELEASE_LEASE',
    escalation: 'QUARANTINE_IF_OWNER_AMBIGUOUS',
    successAllowed: false,
  },
  LEASE_CONTENTION: {
    fault: 'LEASE_CONTENTION',
    jobState: 'BLOCKED',
    profileState: 'UNCHANGED',
    recovery: 'RETRY_AFTER_CURRENT_OWNER_RELEASES',
    escalation: 'QUARANTINE_IF_OWNER_AMBIGUOUS',
    successAllowed: false,
  },
  DISK_ARTIFACT_FAILURE: {
    fault: 'DISK_ARTIFACT_FAILURE',
    jobState: 'FAILED',
    profileState: 'UNCHANGED',
    recovery: 'REPAIR_STORAGE_THEN_BOUNDED_REQUEUE',
    escalation: 'OPERATOR_STORAGE_REPAIR',
    successAllowed: false,
  },
  AUTH_REQUIRED: {
    fault: 'AUTH_REQUIRED',
    jobState: 'WAITING_OPERATOR',
    profileState: 'AUTH_REQUIRED',
    recovery: 'OPERATOR_REAUTHENTICATES_THEN_REQUEUES',
    escalation: 'OPERATOR_AUTHENTICATION_REQUIRED',
    successAllowed: false,
  },
};

export function classifyInjectedFault(fault: FaultKind): FaultDisposition {
  return { ...FAULT_DISPOSITIONS[fault] };
}
