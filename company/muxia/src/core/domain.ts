export const PROVIDER_HEALTH = ['UNKNOWN', 'HEALTHY', 'DEGRADED', 'BLOCKED'] as const;
export type ProviderHealth = (typeof PROVIDER_HEALTH)[number];

export const PROFILE_STATES = [
  'UNINITIALIZED',
  'READY',
  'LEASED',
  'RUNNING',
  'AUTH_REQUIRED',
  'BLOCKED',
  'QUARANTINED',
  'DISABLED',
] as const;
export type ProfileState = (typeof PROFILE_STATES)[number];

export const JOB_STATES = [
  'QUEUED',
  'ASSIGNED',
  'RUNNING',
  'VERIFYING',
  'SUCCEEDED',
  'WAITING_OPERATOR',
  'BLOCKED',
  'FAILED',
  'CANCELLED',
  'TIMED_OUT',
] as const;
export type JobState = (typeof JOB_STATES)[number];

export interface ProviderRecord {
  providerId: string;
  adapterVersion: string;
  capabilities: readonly string[];
  health: ProviderHealth;
}

export interface ProfileRecord {
  profileId: string;
  providerId: string;
  profilePath: string;
  state: ProfileState;
  leaseOwner: string | null;
  browserPid: number | null;
  lastHealthAt: string | null;
  lastSuccessAt: string | null;
  failureCount: number;
}

export interface JobRecord {
  jobId: string;
  providerId: string;
  requiredCapability: string;
  profileSelector: string | null;
  artifactTarget: string;
  timeoutMs: number;
  status: JobState;
  attempt: number;
  createdAt: string;
}

export interface ArtifactReceiptRecord {
  jobId: string;
  profileId: string;
  providerId: string;
  artifactPath: string;
  sha256: string;
  bytes: number;
  mimeType: string;
  createdAt: string;
  adapterVersion: string;
  status: 'VERIFIED';
}

export interface CompletionEvidence {
  artifactExists: boolean;
  receiptExists: boolean;
  hashMatches: boolean;
  bytesMatch: boolean;
  mimeMatches: boolean;
}

const PROFILE_TRANSITIONS: Readonly<Record<ProfileState, readonly ProfileState[]>> = {
  UNINITIALIZED: ['READY', 'AUTH_REQUIRED', 'BLOCKED', 'DISABLED'],
  READY: ['LEASED', 'AUTH_REQUIRED', 'BLOCKED', 'QUARANTINED', 'DISABLED'],
  LEASED: ['RUNNING', 'READY', 'AUTH_REQUIRED', 'BLOCKED', 'QUARANTINED', 'DISABLED'],
  RUNNING: ['LEASED', 'READY', 'AUTH_REQUIRED', 'BLOCKED', 'QUARANTINED', 'DISABLED'],
  AUTH_REQUIRED: ['READY', 'BLOCKED', 'QUARANTINED', 'DISABLED'],
  BLOCKED: ['READY', 'AUTH_REQUIRED', 'QUARANTINED', 'DISABLED'],
  QUARANTINED: ['READY', 'DISABLED'],
  DISABLED: [],
};

const JOB_TRANSITIONS: Readonly<Record<JobState, readonly JobState[]>> = {
  QUEUED: ['ASSIGNED', 'BLOCKED', 'CANCELLED', 'TIMED_OUT'],
  ASSIGNED: ['RUNNING', 'BLOCKED', 'CANCELLED', 'TIMED_OUT'],
  RUNNING: ['VERIFYING', 'WAITING_OPERATOR', 'BLOCKED', 'FAILED', 'CANCELLED', 'TIMED_OUT'],
  VERIFYING: ['SUCCEEDED', 'WAITING_OPERATOR', 'BLOCKED', 'FAILED', 'CANCELLED', 'TIMED_OUT'],
  SUCCEEDED: [],
  WAITING_OPERATOR: ['RUNNING', 'BLOCKED', 'FAILED', 'CANCELLED', 'TIMED_OUT'],
  BLOCKED: ['QUEUED', 'CANCELLED'],
  FAILED: ['QUEUED', 'CANCELLED'],
  CANCELLED: [],
  TIMED_OUT: ['QUEUED', 'CANCELLED'],
};

export function assertProfileTransition(from: ProfileState, to: ProfileState): void {
  if (!PROFILE_TRANSITIONS[from].includes(to)) {
    throw new Error(`INVALID_PROFILE_TRANSITION:${from}->${to}`);
  }
}

export function assertCompletionEvidence(evidence: CompletionEvidence | undefined): void {
  if (!evidence) throw new Error('FALSE_SUCCESS:MISSING_COMPLETION_EVIDENCE');
  const checks: Array<[keyof CompletionEvidence, string]> = [
    ['artifactExists', 'ARTIFACT_MISSING'],
    ['receiptExists', 'RECEIPT_MISSING'],
    ['hashMatches', 'HASH_MISMATCH'],
    ['bytesMatch', 'BYTE_COUNT_MISMATCH'],
    ['mimeMatches', 'MIME_MISMATCH'],
  ];
  for (const [field, code] of checks) {
    if (!evidence[field]) throw new Error(`FALSE_SUCCESS:${code}`);
  }
}

export function assertJobTransition(
  from: JobState,
  to: JobState,
  evidence?: CompletionEvidence,
): void {
  if (!JOB_TRANSITIONS[from].includes(to)) {
    throw new Error(`INVALID_JOB_TRANSITION:${from}->${to}`);
  }
  if (to === 'SUCCEEDED') assertCompletionEvidence(evidence);
}

export function acquireProfileLease(profile: ProfileRecord, owner: string): ProfileRecord {
  if (!owner.trim()) throw new Error('LEASE_OWNER_REQUIRED');
  if (profile.leaseOwner !== null) throw new Error('DUPLICATE_PROFILE_LEASE');
  if (profile.state !== 'READY') throw new Error(`PROFILE_NOT_READY:${profile.state}`);
  assertProfileTransition(profile.state, 'LEASED');
  return { ...profile, state: 'LEASED', leaseOwner: owner };
}

export function releaseProfileLease(profile: ProfileRecord, owner: string): ProfileRecord {
  if (profile.leaseOwner === null) throw new Error('PROFILE_NOT_LEASED');
  if (profile.leaseOwner !== owner) throw new Error('LEASE_OWNER_MISMATCH');
  if (profile.state !== 'LEASED' && profile.state !== 'RUNNING') {
    throw new Error(`PROFILE_NOT_RELEASABLE:${profile.state}`);
  }
  assertProfileTransition(profile.state, 'READY');
  return { ...profile, state: 'READY', leaseOwner: null, browserPid: null };
}

export function markProfileRunning(profile: ProfileRecord, owner: string, browserPid: number): ProfileRecord {
  if (profile.leaseOwner !== owner) throw new Error('LEASE_OWNER_MISMATCH');
  if (profile.state !== 'LEASED') throw new Error(`PROFILE_NOT_LEASED:${profile.state}`);
  if (!Number.isInteger(browserPid) || browserPid <= 0) throw new Error('INVALID_BROWSER_PID');
  assertProfileTransition(profile.state, 'RUNNING');
  return { ...profile, state: 'RUNNING', browserPid };
}

export function transitionJob(
  job: JobRecord,
  next: JobState,
  evidence?: CompletionEvidence,
): JobRecord {
  assertJobTransition(job.status, next, evidence);
  return { ...job, status: next };
}
