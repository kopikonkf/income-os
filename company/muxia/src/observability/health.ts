import type { JobState, ProfileState, ProviderRecord } from '../core/domain.js';
import type { JobRegistry } from '../core/job-registry.js';
import type { ProfileRegistry } from '../core/profile-registry.js';
import { safeDiagnosticCode } from './sanitized-logging.js';

export type HealthGrade = 'HEALTHY' | 'DEGRADED' | 'BLOCKED';
export type ProcessHealth = 'ALIVE' | 'DEAD' | 'MISSING' | 'NONE' | 'STALE';
export type ArtifactHealth = 'VERIFIED' | 'INVALID' | 'NOT_EXPECTED';

export interface SanitizedProfileHealth {
  profileId: string;
  providerId: string;
  state: ProfileState;
  leaseActive: boolean;
  process: ProcessHealth;
  failureCount: number;
  lastHealthAt: string | null;
  lastSuccessAt: string | null;
  issueCodes: string[];
}

export interface SanitizedJobHealth {
  jobId: string;
  providerId: string;
  requiredCapability: string;
  profileSelector: string | null;
  status: JobState;
  attempt: number;
  artifact: ArtifactHealth;
  issueCodes: string[];
}

export interface SanitizedHealthSnapshot {
  schema: 'die.muxia.sanitized-health.v1';
  observedAt: string;
  grade: HealthGrade;
  counts: {
    providers: number;
    profiles: number;
    jobs: number;
    activeLeases: number;
    runningJobs: number;
    blockedItems: number;
  };
  providers: Array<Pick<ProviderRecord, 'providerId' | 'adapterVersion' | 'capabilities' | 'health'>>;
  profiles: SanitizedProfileHealth[];
  jobs: SanitizedJobHealth[];
}

function inspectProcess(state: ProfileState, pid: number | null, isProcessAlive: (pid: number) => boolean): ProcessHealth {
  if (state === 'RUNNING') {
    if (pid === null) return 'MISSING';
    return isProcessAlive(pid) ? 'ALIVE' : 'DEAD';
  }
  return pid === null ? 'NONE' : 'STALE';
}

function profileIssues(state: ProfileState, process: ProcessHealth, leaseActive: boolean, failureCount: number): string[] {
  const issues: string[] = [];
  if (state === 'AUTH_REQUIRED') issues.push('AUTH_REQUIRED');
  if (state === 'BLOCKED') issues.push('PROFILE_BLOCKED');
  if (state === 'QUARANTINED') issues.push('PROFILE_QUARANTINED');
  if (process === 'DEAD') issues.push('RUNNING_PROCESS_DEAD');
  if (process === 'MISSING') issues.push('RUNNING_PROCESS_MISSING');
  if (process === 'STALE') issues.push('STALE_PROCESS_REFERENCE');
  if (leaseActive !== ['LEASED', 'RUNNING'].includes(state)) issues.push('LEASE_STATE_MISMATCH');
  if (failureCount > 0) issues.push('FAILURE_HISTORY');
  return issues;
}

function artifactHealth(jobRegistry: JobRegistry, jobId: string, status: JobState): { artifact: ArtifactHealth; issueCodes: string[] } {
  if (status !== 'VERIFYING' && status !== 'SUCCEEDED') return { artifact: 'NOT_EXPECTED', issueCodes: [] };
  try {
    jobRegistry.verifyArtifact(jobId);
    return { artifact: 'VERIFIED', issueCodes: [] };
  } catch (error) {
    return { artifact: 'INVALID', issueCodes: [safeDiagnosticCode(error)] };
  }
}

export function buildSanitizedHealthSnapshot(options: {
  providers: readonly ProviderRecord[];
  profileRegistry: ProfileRegistry;
  jobRegistry: JobRegistry;
  isProcessAlive: (pid: number) => boolean;
  observedAt?: string;
}): SanitizedHealthSnapshot {
  const providers = [...options.providers]
    .sort((a, b) => a.providerId.localeCompare(b.providerId))
    .map(({ providerId, adapterVersion, capabilities, health }) => ({
      providerId,
      adapterVersion,
      capabilities: [...capabilities].sort(),
      health,
    }));

  const profiles = options.profileRegistry.list()
    .sort((a, b) => a.profileId.localeCompare(b.profileId))
    .map((profile): SanitizedProfileHealth => {
      const process = inspectProcess(profile.state, profile.browserPid, options.isProcessAlive);
      const leaseActive = profile.leaseOwner !== null;
      return {
        profileId: profile.profileId,
        providerId: profile.providerId,
        state: profile.state,
        leaseActive,
        process,
        failureCount: profile.failureCount,
        lastHealthAt: profile.lastHealthAt,
        lastSuccessAt: profile.lastSuccessAt,
        issueCodes: profileIssues(profile.state, process, leaseActive, profile.failureCount),
      };
    });

  const jobs = options.jobRegistry.list()
    .sort((a, b) => a.jobId.localeCompare(b.jobId))
    .map((job): SanitizedJobHealth => {
      const artifact = artifactHealth(options.jobRegistry, job.jobId, job.status);
      const issueCodes = [...artifact.issueCodes];
      if (['BLOCKED', 'FAILED', 'TIMED_OUT', 'WAITING_OPERATOR'].includes(job.status)) issueCodes.push(`JOB_${job.status}`);
      return {
        jobId: job.jobId,
        providerId: job.providerId,
        requiredCapability: job.requiredCapability,
        profileSelector: job.profileSelector,
        status: job.status,
        attempt: job.attempt,
        artifact: artifact.artifact,
        issueCodes,
      };
    });

  const blockedItems = providers.filter((provider) => provider.health === 'BLOCKED').length
    + profiles.filter((profile) => ['AUTH_REQUIRED', 'BLOCKED', 'QUARANTINED'].includes(profile.state)).length
    + jobs.filter((job) => ['BLOCKED', 'FAILED', 'TIMED_OUT', 'WAITING_OPERATOR'].includes(job.status)).length;
  const degraded = providers.some((provider) => provider.health === 'DEGRADED')
    || profiles.some((profile) => profile.issueCodes.length > 0)
    || jobs.some((job) => job.issueCodes.length > 0);

  return {
    schema: 'die.muxia.sanitized-health.v1',
    observedAt: options.observedAt ?? new Date().toISOString(),
    grade: blockedItems > 0 ? 'BLOCKED' : degraded ? 'DEGRADED' : 'HEALTHY',
    counts: {
      providers: providers.length,
      profiles: profiles.length,
      jobs: jobs.length,
      activeLeases: profiles.filter((profile) => profile.leaseActive).length,
      runningJobs: jobs.filter((job) => job.status === 'RUNNING').length,
      blockedItems,
    },
    providers,
    profiles,
    jobs,
  };
}
