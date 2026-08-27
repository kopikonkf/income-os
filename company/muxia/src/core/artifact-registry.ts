import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import type { ArtifactReceiptRecord, CompletionEvidence, JobRecord } from './domain.js';
import type { MuxiaPaths } from './paths.js';
import { assertSafeId, isPathInside } from './paths.js';
import { ensureMuxiaLayout, readJsonFile, writeJsonAtomic } from './storage.js';

function sha256(buffer: Buffer): string {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function detectRasterMime(buffer: Buffer): string {
  if (
    buffer.length >= 8 &&
    buffer[0] === 0x89 && buffer[1] === 0x50 && buffer[2] === 0x4e && buffer[3] === 0x47 &&
    buffer[4] === 0x0d && buffer[5] === 0x0a && buffer[6] === 0x1a && buffer[7] === 0x0a
  ) return 'image/png';

  if (buffer.length >= 3 && buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff) {
    return 'image/jpeg';
  }

  if (
    buffer.length >= 12 &&
    buffer.subarray(0, 4).toString('ascii') === 'RIFF' &&
    buffer.subarray(8, 12).toString('ascii') === 'WEBP'
  ) return 'image/webp';

  throw new Error('UNSUPPORTED_RASTER_CONTAINER');
}

export class ArtifactRegistry {
  constructor(private readonly paths: MuxiaPaths) {
    ensureMuxiaLayout(paths);
  }

  private receiptFile(jobId: string): string {
    assertSafeId(jobId, 'job');
    return path.join(this.paths.receipts, `${jobId}.json`);
  }

  registerForJob(
    job: JobRecord,
    profileId: string,
    adapterVersion: string,
    artifactPath: string,
    createdAt = new Date().toISOString(),
  ): ArtifactReceiptRecord {
    assertSafeId(job.jobId, 'job');
    assertSafeId(job.providerId, 'provider');
    assertSafeId(profileId, 'profile');
    if (!adapterVersion.trim()) throw new Error('ADAPTER_VERSION_REQUIRED');
    if (job.status !== 'VERIFYING') throw new Error(`JOB_NOT_VERIFYING:${job.status}`);
    if (!isPathInside(this.paths.artifacts, artifactPath)) throw new Error('ARTIFACT_OUTSIDE_MUXIA_ROOT');
    if (!isPathInside(job.artifactTarget, artifactPath)) throw new Error('ARTIFACT_OUTSIDE_JOB_TARGET');
    if (!fs.existsSync(artifactPath)) throw new Error('ARTIFACT_MISSING');

    const file = this.receiptFile(job.jobId);
    if (fs.existsSync(file)) throw new Error('ARTIFACT_RECEIPT_ALREADY_EXISTS');

    const buffer = fs.readFileSync(artifactPath);
    if (buffer.length === 0) throw new Error('ARTIFACT_EMPTY');
    const mimeType = detectRasterMime(buffer);
    const receipt: ArtifactReceiptRecord = {
      jobId: job.jobId,
      profileId,
      providerId: job.providerId,
      artifactPath: path.resolve(artifactPath),
      sha256: sha256(buffer),
      bytes: buffer.length,
      mimeType,
      createdAt,
      adapterVersion: adapterVersion.trim(),
      status: 'VERIFIED',
    };
    writeJsonAtomic(file, receipt);
    return this.getForJob(job.jobId);
  }

  getForJob(jobId: string): ArtifactReceiptRecord {
    const file = this.receiptFile(jobId);
    if (!fs.existsSync(file)) throw new Error('ARTIFACT_RECEIPT_NOT_FOUND');
    const receipt = readJsonFile<ArtifactReceiptRecord>(file);
    assertSafeId(receipt.jobId, 'job');
    assertSafeId(receipt.profileId, 'profile');
    assertSafeId(receipt.providerId, 'provider');
    if (!/^[0-9a-f]{64}$/.test(receipt.sha256)) throw new Error('INVALID_ARTIFACT_SHA256');
    if (!Number.isInteger(receipt.bytes) || receipt.bytes <= 0) throw new Error('INVALID_ARTIFACT_BYTES');
    return receipt;
  }

  verifyForJob(job: JobRecord): CompletionEvidence {
    const receipt = this.getForJob(job.jobId);
    if (receipt.jobId !== job.jobId) throw new Error('ARTIFACT_JOB_MISMATCH');
    if (receipt.providerId !== job.providerId) throw new Error('ARTIFACT_PROVIDER_MISMATCH');
    if (job.profileSelector !== null && receipt.profileId !== job.profileSelector) throw new Error('ARTIFACT_PROFILE_MISMATCH');
    if (!isPathInside(this.paths.artifacts, receipt.artifactPath)) throw new Error('ARTIFACT_OUTSIDE_MUXIA_ROOT');
    if (!isPathInside(job.artifactTarget, receipt.artifactPath)) throw new Error('ARTIFACT_OUTSIDE_JOB_TARGET');
    if (!fs.existsSync(receipt.artifactPath)) throw new Error('ARTIFACT_MISSING');

    const buffer = fs.readFileSync(receipt.artifactPath);
    const actualHash = sha256(buffer);
    const actualMime = detectRasterMime(buffer);
    if (actualHash !== receipt.sha256) throw new Error('ARTIFACT_HASH_MISMATCH');
    if (buffer.length !== receipt.bytes) throw new Error('ARTIFACT_BYTE_COUNT_MISMATCH');
    if (actualMime !== receipt.mimeType) throw new Error('ARTIFACT_MIME_MISMATCH');

    return {
      artifactExists: true,
      receiptExists: true,
      hashMatches: true,
      bytesMatch: true,
      mimeMatches: true,
    };
  }
}
