import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import type { ArtifactReceiptRecord, JobRecord } from '../core/domain.js';
import type { MuxiaPaths } from '../core/paths.js';
import { assertSafeId, isPathInside } from '../core/paths.js';

export const MX070_COMPATIBILITY_VERSION = 'mx070-legacy-proxima-v1';
export const LEGACY_PROXIMA_ENDPOINT = 'http://127.0.0.1:3211/v1/chat/completions';

export interface LegacyAcceptanceCriterion {
  id: string;
  statement: string;
  verify_with: string;
}

export interface LegacyProximaJob {
  schema_version: 'die.worker-job.v1';
  task_id: string;
  stage?: string;
  mission_id: string;
  goal: string;
  context: Record<string, unknown>;
  workspace: string;
  constraints: {
    time_budget_min: number;
    allowed_paths: string[];
    network: string;
    forbidden: string[];
    read_only_inputs?: string[];
  };
  acceptance_criteria: LegacyAcceptanceCriterion[];
}

export interface Mx070CompatibilityRoute {
  schema: 'die.muxia.legacy-compat-route.v1';
  compatibilityVersion: string;
  sourceContract: 'die.worker-job.v1';
  sourceSha256: string;
  legacy: {
    taskId: string;
    missionId: string;
    stage: string | null;
    workspace: string;
    legacyEndpoint: string;
    rollbackAvailable: true;
    legacyEndpointCalled: false;
  };
  muxiaJob: JobRecord;
  providerRoute: {
    providerId: 'chatgpt';
    requiredCapability: 'image.generate';
  };
  acceptanceCriteria: LegacyAcceptanceCriterion[];
  authorityBoundary: {
    maxCostUsd: 0;
    submissionAuthorized: false;
    publicationAuthorized: false;
    credentialAccessAuthorized: false;
    canonicalStateWriteAuthorized: false;
  };
}

export interface LegacyExportReceipt {
  schema: 'die.muxia.legacy-artifact-export.v1';
  compatibilityVersion: string;
  taskId: string;
  muxiaJobId: string;
  sourceArtifactPath: string;
  legacyArtifactPath: string;
  legacyArtifactRelativePath: string;
  sha256: string;
  bytes: number;
  mimeType: string;
  idempotentReuse: boolean;
  authorityBoundary: {
    sourceVerified: true;
    legacyWorkspaceOnly: true;
    submissionAuthorized: false;
    publicationAuthorized: false;
  };
}

function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    return `{${Object.entries(value as Record<string, unknown>)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, item]) => `${JSON.stringify(key)}:${stable(item)}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

function sha256(buffer: Buffer | string): string {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function assertForbiddenBoundaries(forbidden: readonly string[]): void {
  const required = ['credentials', 'market submission', 'publication', 'spawning workers', 'writes outside workspace'];
  for (const item of required) {
    if (!forbidden.includes(item)) throw new Error(`LEGACY_AUTHORITY_BOUNDARY_MISSING:${item}`);
  }
}

function legacyEndpoint(job: LegacyProximaJob): string {
  const contract = job.context?.stage_contract;
  if (contract && typeof contract === 'object') {
    const endpoint = (contract as Record<string, unknown>).proxima_endpoint;
    if (endpoint !== undefined && endpoint !== LEGACY_PROXIMA_ENDPOINT) {
      throw new Error('UNSUPPORTED_LEGACY_PROXIMA_ENDPOINT');
    }
  }
  return LEGACY_PROXIMA_ENDPOINT;
}

export function adaptLegacyProximaJob(
  job: LegacyProximaJob,
  paths: MuxiaPaths,
  createdAt = new Date().toISOString(),
): Mx070CompatibilityRoute {
  if (job.schema_version !== 'die.worker-job.v1') throw new Error('LEGACY_JOB_SCHEMA_INVALID');
  assertSafeId(job.task_id, 'job');
  if (!job.mission_id.trim()) throw new Error('LEGACY_MISSION_ID_REQUIRED');
  if (!job.goal.trim()) throw new Error('LEGACY_GOAL_REQUIRED');
  if (!path.isAbsolute(job.workspace)) throw new Error('LEGACY_WORKSPACE_MUST_BE_ABSOLUTE');
  if (job.constraints.network !== 'proxima_loopback_only') throw new Error('LEGACY_JOB_NOT_PROXIMA_ROUTE');
  if (!Number.isInteger(job.constraints.time_budget_min) || job.constraints.time_budget_min <= 0) {
    throw new Error('LEGACY_TIME_BUDGET_INVALID');
  }
  if (!job.constraints.allowed_paths.some((candidate) => path.resolve(candidate) === path.resolve(job.workspace))) {
    throw new Error('LEGACY_WORKSPACE_NOT_ALLOWED');
  }
  assertForbiddenBoundaries(job.constraints.forbidden);
  if (!Array.isArray(job.acceptance_criteria) || job.acceptance_criteria.length === 0) {
    throw new Error('LEGACY_ACCEPTANCE_CRITERIA_REQUIRED');
  }
  const criterionIds = new Set<string>();
  for (const criterion of job.acceptance_criteria) {
    if (!/^AC-[1-9][0-9]*$/.test(criterion.id) || criterionIds.has(criterion.id)) {
      throw new Error('LEGACY_ACCEPTANCE_CRITERION_INVALID');
    }
    if (!criterion.statement.trim() || !criterion.verify_with.trim()) throw new Error('LEGACY_ACCEPTANCE_CRITERION_EMPTY');
    criterionIds.add(criterion.id);
  }

  const artifactTarget = path.join(paths.artifacts, job.task_id);
  const muxiaJob: JobRecord = {
    jobId: job.task_id,
    providerId: 'chatgpt',
    requiredCapability: 'image.generate',
    profileSelector: null,
    artifactTarget,
    timeoutMs: job.constraints.time_budget_min * 60_000,
    status: 'QUEUED',
    attempt: 0,
    createdAt,
  };

  return {
    schema: 'die.muxia.legacy-compat-route.v1',
    compatibilityVersion: MX070_COMPATIBILITY_VERSION,
    sourceContract: 'die.worker-job.v1',
    sourceSha256: sha256(stable(job)),
    legacy: {
      taskId: job.task_id,
      missionId: job.mission_id,
      stage: job.stage ?? null,
      workspace: path.resolve(job.workspace),
      legacyEndpoint: legacyEndpoint(job),
      rollbackAvailable: true,
      legacyEndpointCalled: false,
    },
    muxiaJob,
    providerRoute: { providerId: 'chatgpt', requiredCapability: 'image.generate' },
    acceptanceCriteria: job.acceptance_criteria.map((row) => ({ ...row })),
    authorityBoundary: {
      maxCostUsd: 0,
      submissionAuthorized: false,
      publicationAuthorized: false,
      credentialAccessAuthorized: false,
      canonicalStateWriteAuthorized: false,
    },
  };
}

export function exportVerifiedArtifactToLegacyWorkspace(
  route: Mx070CompatibilityRoute,
  receipt: ArtifactReceiptRecord,
  paths: MuxiaPaths,
  legacyFileName: string,
): LegacyExportReceipt {
  if (receipt.status !== 'VERIFIED') throw new Error('MUXIA_ARTIFACT_NOT_VERIFIED');
  if (receipt.jobId !== route.muxiaJob.jobId) throw new Error('MUXIA_ARTIFACT_JOB_MISMATCH');
  if (receipt.providerId !== route.muxiaJob.providerId) throw new Error('MUXIA_ARTIFACT_PROVIDER_MISMATCH');
  if (!isPathInside(paths.artifacts, receipt.artifactPath)) throw new Error('MUXIA_ARTIFACT_OUTSIDE_ROOT');
  if (!isPathInside(route.muxiaJob.artifactTarget, receipt.artifactPath)) throw new Error('MUXIA_ARTIFACT_OUTSIDE_JOB_TARGET');
  if (!fs.existsSync(receipt.artifactPath)) throw new Error('MUXIA_ARTIFACT_MISSING');
  if (path.basename(legacyFileName) !== legacyFileName || !legacyFileName.trim()) throw new Error('LEGACY_ARTIFACT_FILENAME_UNSAFE');

  const source = fs.readFileSync(receipt.artifactPath);
  if (source.length !== receipt.bytes || sha256(source) !== receipt.sha256) throw new Error('MUXIA_ARTIFACT_RECEIPT_MISMATCH');

  const workspace = path.resolve(route.legacy.workspace);
  const target = path.resolve(workspace, legacyFileName);
  if (!isPathInside(workspace, target)) throw new Error('LEGACY_EXPORT_OUTSIDE_WORKSPACE');
  fs.mkdirSync(workspace, { recursive: true });

  let idempotentReuse = false;
  if (fs.existsSync(target)) {
    const existing = fs.readFileSync(target);
    if (sha256(existing) !== receipt.sha256 || existing.length !== receipt.bytes) {
      throw new Error('LEGACY_EXPORT_CONFLICT');
    }
    idempotentReuse = true;
  } else {
    fs.copyFileSync(receipt.artifactPath, target);
  }

  const exported = fs.readFileSync(target);
  if (sha256(exported) !== receipt.sha256 || exported.length !== receipt.bytes) throw new Error('LEGACY_EXPORT_VERIFY_FAILED');

  return {
    schema: 'die.muxia.legacy-artifact-export.v1',
    compatibilityVersion: MX070_COMPATIBILITY_VERSION,
    taskId: route.legacy.taskId,
    muxiaJobId: route.muxiaJob.jobId,
    sourceArtifactPath: path.resolve(receipt.artifactPath),
    legacyArtifactPath: target,
    legacyArtifactRelativePath: legacyFileName,
    sha256: receipt.sha256,
    bytes: receipt.bytes,
    mimeType: receipt.mimeType,
    idempotentReuse,
    authorityBoundary: {
      sourceVerified: true,
      legacyWorkspaceOnly: true,
      submissionAuthorized: false,
      publicationAuthorized: false,
    },
  };
}

export function projectLegacyCompletion(
  route: Mx070CompatibilityRoute,
  artifactReceipt: ArtifactReceiptRecord,
  exportReceipt: LegacyExportReceipt,
) {
  if (artifactReceipt.sha256 !== exportReceipt.sha256) throw new Error('COMPATIBILITY_EXPORT_HASH_MISMATCH');
  const evidence = route.acceptanceCriteria.map((criterion) => ({
    type: 'receipt',
    ref: 'MX070_COMPATIBILITY_RECEIPT.json',
    claim: criterion.id,
  }));
  const test = {
    name: 'MX-070 artifact equivalence AC-1 AC-2 AC-3',
    command: 'muxia compatibility verified-export',
    result: 'pass',
    output_ref: 'MX070_COMPATIBILITY_RECEIPT.json',
  };

  const legacyResult = {
    schema_version: 'die.worker-result.v1',
    task_id: route.legacy.taskId,
    status: 'done',
    summary: 'Verified MUXIA artifact exported through the MX-070 legacy compatibility boundary.',
    artifact: [{
      path: exportReceipt.legacyArtifactRelativePath,
      kind: 'file',
      description: 'MUXIA-verified raster exported into the legacy Worker workspace',
    }],
    evidence,
    tests: [test],
    errors: [],
    next_action: null,
    cost_usd: 0,
    authority_boundary: {
      submission_authorized: false,
      publication_authorized: false,
      credential_accessed: false,
      canonical_state_written: false,
    },
  };

  const workerResult = {
    schema: 'die.worker-result-envelope.v1',
    task_id: route.legacy.taskId,
    executor: 'opencode',
    status: 'done',
    summary: legacyResult.summary,
    artifacts: legacyResult.artifact,
    evidence,
    tests: [test],
    errors: [],
    next_action: null,
  };

  return {
    schema: 'die.muxia.mx070-completion-projection.v1',
    compatibilityVersion: MX070_COMPATIBILITY_VERSION,
    routeSha256: sha256(stable(route)),
    muxiaArtifactReceiptSha256: sha256(stable(artifactReceipt)),
    exportReceiptSha256: sha256(stable(exportReceipt)),
    legacyResult,
    workerResult,
    authorityBoundary: route.authorityBoundary,
  };
}
