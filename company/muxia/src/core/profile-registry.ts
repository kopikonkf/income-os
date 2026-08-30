import fs from 'node:fs';
import path from 'node:path';
import type { MuxiaPaths } from './paths.js';
import { assertSafeId, isPathInside } from './paths.js';
import type { ProfileRecord } from './domain.js';
import { acquireProfileLease, assertProfileTransition, releaseProfileLease } from './domain.js';
import { assertNoSecretLikeKeys, ensureMuxiaLayout, listJsonFiles, readJsonFile, writeJsonAtomic } from './storage.js';

const PROFILE_FIELDS = new Set([
  'profileId', 'providerId', 'profilePath', 'state', 'leaseOwner', 'browserPid',
  'lastHealthAt', 'lastSuccessAt', 'failureCount',
]);

interface LeaseRecord {
  profileId: string;
  owner: string;
  acquiredAt: string;
}

function assertExactFields(record: Record<string, unknown>): void {
  for (const key of Object.keys(record)) {
    if (!PROFILE_FIELDS.has(key)) throw new Error(`UNKNOWN_PROFILE_FIELD:${key}`);
  }
}

function assertProfileShape(profile: ProfileRecord, paths: MuxiaPaths): void {
  assertNoSecretLikeKeys(profile);
  assertExactFields(profile as unknown as Record<string, unknown>);
  assertSafeId(profile.profileId, 'profile');
  assertSafeId(profile.providerId, 'provider');
  if (!isPathInside(paths.profiles, profile.profilePath)) throw new Error('PROFILE_PATH_OUTSIDE_ROOT');
  if (!Number.isInteger(profile.failureCount) || profile.failureCount < 0) throw new Error('INVALID_FAILURE_COUNT');
  if (profile.browserPid !== null && (!Number.isInteger(profile.browserPid) || profile.browserPid <= 0)) {
    throw new Error('INVALID_BROWSER_PID');
  }
}

export class ProfileRegistry {
  private readonly profilesStateDir: string;

  constructor(private readonly paths: MuxiaPaths) {
    ensureMuxiaLayout(paths);
    this.profilesStateDir = path.join(paths.state, 'profiles');
    fs.mkdirSync(this.profilesStateDir, { recursive: true });
  }

  private profileFile(profileId: string): string {
    assertSafeId(profileId, 'profile');
    return path.join(this.profilesStateDir, `${profileId}.json`);
  }

  private leaseFile(profileId: string): string {
    assertSafeId(profileId, 'profile');
    return path.join(this.paths.locks, `profile-${profileId}.lease.json`);
  }

  create(profile: ProfileRecord): ProfileRecord {
    assertProfileShape(profile, this.paths);
    const file = this.profileFile(profile.profileId);
    if (fs.existsSync(file)) throw new Error('PROFILE_ALREADY_EXISTS');
    if (profile.leaseOwner !== null) throw new Error('PROFILE_CREATE_WITH_LEASE_FORBIDDEN');
    writeJsonAtomic(file, profile);
    return this.get(profile.profileId);
  }

  get(profileId: string): ProfileRecord {
    const file = this.profileFile(profileId);
    if (!fs.existsSync(file)) throw new Error('PROFILE_NOT_FOUND');
    const profile = readJsonFile<ProfileRecord>(file);
    assertProfileShape(profile, this.paths);
    return profile;
  }

  list(): ProfileRecord[] {
    return listJsonFiles(this.profilesStateDir).map((file) => {
      const profile = readJsonFile<ProfileRecord>(file);
      assertProfileShape(profile, this.paths);
      return profile;
    });
  }

  update(profile: ProfileRecord): ProfileRecord {
    assertProfileShape(profile, this.paths);
    const file = this.profileFile(profile.profileId);
    if (!fs.existsSync(file)) throw new Error('PROFILE_NOT_FOUND');
    const current = this.get(profile.profileId);
    if (current.leaseOwner !== profile.leaseOwner) throw new Error('LEASE_OWNER_MUTATION_FORBIDDEN');
    writeJsonAtomic(file, profile);
    return this.get(profile.profileId);
  }

  remove(profileId: string): void {
    const file = this.profileFile(profileId);
    if (!fs.existsSync(file)) throw new Error('PROFILE_NOT_FOUND');
    if (fs.existsSync(this.leaseFile(profileId))) throw new Error('PROFILE_LEASE_ACTIVE');
    fs.rmSync(file);
  }

  acquireLease(profileId: string, owner: string, now = new Date().toISOString()): ProfileRecord {
    assertSafeId(owner, 'lease_owner');
    const lock = this.leaseFile(profileId);
    let fd: number | undefined;
    try {
      fd = fs.openSync(lock, 'wx', 0o600);
      const lease: LeaseRecord = { profileId, owner, acquiredAt: now };
      fs.writeFileSync(fd, `${JSON.stringify(lease, null, 2)}\n`, 'utf8');
      fs.fsyncSync(fd);
      fs.closeSync(fd);
      fd = undefined;

      const next = acquireProfileLease(this.get(profileId), owner);
      writeJsonAtomic(this.profileFile(profileId), next);
      return this.get(profileId);
    } catch (error) {
      if (fd !== undefined) fs.closeSync(fd);
      if ((error as NodeJS.ErrnoException).code === 'EEXIST') throw new Error('DUPLICATE_PROFILE_LEASE');
      if (fs.existsSync(lock)) {
        try {
          const lease = readJsonFile<LeaseRecord>(lock);
          if (lease.owner === owner && lease.profileId === profileId) fs.rmSync(lock, { force: true });
        } catch {
          // Leave ambiguous lock in place: fail closed.
        }
      }
      throw error;
    }
  }

  releaseLease(profileId: string, owner: string): ProfileRecord {
    assertSafeId(owner, 'lease_owner');
    const lock = this.leaseFile(profileId);
    if (!fs.existsSync(lock)) throw new Error('PROFILE_NOT_LEASED');
    const lease = readJsonFile<LeaseRecord>(lock);
    if (lease.owner !== owner || lease.profileId !== profileId) throw new Error('LEASE_OWNER_MISMATCH');

    const next = releaseProfileLease(this.get(profileId), owner);
    writeJsonAtomic(this.profileFile(profileId), next);
    fs.rmSync(lock);
    return this.get(profileId);
  }

  requireAuthentication(
    profileId: string,
    owner: string,
    now = new Date().toISOString(),
  ): ProfileRecord {
    assertSafeId(owner, 'lease_owner');
    const lock = this.leaseFile(profileId);
    if (!fs.existsSync(lock)) throw new Error('PROFILE_NOT_LEASED');
    const lease = readJsonFile<LeaseRecord>(lock);
    const current = this.get(profileId);
    if (lease.owner !== owner || lease.profileId !== profileId || current.leaseOwner !== owner) {
      throw new Error('LEASE_OWNER_MISMATCH');
    }
    assertProfileTransition(current.state, 'AUTH_REQUIRED');

    const next: ProfileRecord = {
      ...current,
      state: 'AUTH_REQUIRED',
      leaseOwner: null,
      browserPid: null,
      lastHealthAt: now,
      failureCount: current.failureCount + 1,
    };
    writeJsonAtomic(this.profileFile(profileId), next);
    fs.rmSync(lock);
    return this.get(profileId);
  }
}
