import type { ProfileRegistry } from './profile-registry.js';
import type { JobRegistry } from './job-registry.js';

export interface CrashRecoveryResult {
  profileId: string;
  jobId: string;
  action: 'NOOP_PROCESS_ALIVE' | 'RECOVERED_READY' | 'QUARANTINE_REQUIRED';
  jobStatus: string;
  profileState: string;
  reason: string;
}

export function recoverCrashedAssignment(options: {
  profileRegistry: ProfileRegistry;
  jobRegistry: JobRegistry;
  profileId: string;
  jobId: string;
  expectedOwner: string;
  isProcessAlive: (pid: number) => boolean;
}): CrashRecoveryResult {
  const { profileRegistry, jobRegistry, profileId, jobId, expectedOwner, isProcessAlive } = options;
  const profile = profileRegistry.get(profileId);
  const job = jobRegistry.get(jobId);

  if (profile.state !== 'RUNNING') {
    return {
      profileId,
      jobId,
      action: 'QUARANTINE_REQUIRED',
      jobStatus: job.status,
      profileState: profile.state,
      reason: `PROFILE_NOT_RUNNING:${profile.state}`,
    };
  }
  if (profile.leaseOwner !== expectedOwner) {
    return {
      profileId,
      jobId,
      action: 'QUARANTINE_REQUIRED',
      jobStatus: job.status,
      profileState: profile.state,
      reason: 'LEASE_OWNER_AMBIGUOUS',
    };
  }
  if (profile.browserPid === null) {
    return {
      profileId,
      jobId,
      action: 'QUARANTINE_REQUIRED',
      jobStatus: job.status,
      profileState: profile.state,
      reason: 'RUNNING_PROFILE_WITHOUT_PID',
    };
  }
  if (isProcessAlive(profile.browserPid)) {
    return {
      profileId,
      jobId,
      action: 'NOOP_PROCESS_ALIVE',
      jobStatus: job.status,
      profileState: profile.state,
      reason: 'PROCESS_STILL_ALIVE',
    };
  }

  if (job.status === 'RUNNING' || job.status === 'VERIFYING') {
    jobRegistry.transition(jobId, 'FAILED');
  } else if (!['FAILED', 'CANCELLED', 'TIMED_OUT', 'BLOCKED'].includes(job.status)) {
    return {
      profileId,
      jobId,
      action: 'QUARANTINE_REQUIRED',
      jobStatus: job.status,
      profileState: profile.state,
      reason: `JOB_STATE_NOT_RECOVERABLE:${job.status}`,
    };
  }

  try {
    const released = profileRegistry.releaseLease(profileId, expectedOwner);
    return {
      profileId,
      jobId,
      action: 'RECOVERED_READY',
      jobStatus: jobRegistry.get(jobId).status,
      profileState: released.state,
      reason: 'CRASHED_PROCESS_JOB_FAILED_LEASE_RELEASED',
    };
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    return {
      profileId,
      jobId,
      action: 'QUARANTINE_REQUIRED',
      jobStatus: jobRegistry.get(jobId).status,
      profileState: profileRegistry.get(profileId).state,
      reason: `LEASE_RELEASE_FAILED:${detail}`,
    };
  }
}
