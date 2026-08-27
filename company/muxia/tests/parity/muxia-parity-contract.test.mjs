import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CONTRACT_PATH = path.resolve(HERE, '..', '..', 'contracts', 'muxia.parity-contract.v1.json');
const FIXTURE_PATH = path.resolve(HERE, 'fixtures', 'legacy-proxima-postfix-v1.json');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function detectRaster(buffer) {
  if (buffer.length >= 8 &&
      buffer[0] === 0x89 && buffer[1] === 0x50 && buffer[2] === 0x4e && buffer[3] === 0x47 &&
      buffer[4] === 0x0d && buffer[5] === 0x0a && buffer[6] === 0x1a && buffer[7] === 0x0a) {
    return { mime_type: 'image/png', extension: 'png' };
  }
  if (buffer.length >= 3 && buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff) {
    return { mime_type: 'image/jpeg', extension: 'jpg' };
  }
  if (buffer.length >= 12 &&
      buffer.subarray(0, 4).toString('ascii') === 'RIFF' &&
      buffer.subarray(8, 12).toString('ascii') === 'WEBP') {
    return { mime_type: 'image/webp', extension: 'webp' };
  }
  throw new Error('UNSUPPORTED_RASTER_CONTAINER');
}

function assertSha256(value, fieldName) {
  assert.match(value, /^[0-9a-f]{64}$/, `${fieldName} must be lowercase SHA-256 hex`);
}

function verifyDurableEvidence(fixture) {
  const contract = readJson(CONTRACT_PATH);
  const expected = fixture.expected;

  assert.equal(contract.source_policy, 'clean-implementation');
  assert.equal(contract.legacy_source_code_reuse, false);
  assert.deepEqual(contract.runtime_dependencies, []);
  assert.ok(contract.forbidden_runtime_dependencies.includes('electron'));

  assert.ok(fs.existsSync(fixture.probe_receipt_path), 'PROBE_RECEIPT_MISSING');
  assert.ok(fs.existsSync(fixture.artifact_path), 'ARTIFACT_MISSING');
  assert.ok(fs.existsSync(fixture.artifact_receipt_path), 'ARTIFACT_RECEIPT_MISSING');

  const probe = readJson(fixture.probe_receipt_path);
  const receipt = readJson(fixture.artifact_receipt_path);
  const artifact = fs.readFileSync(fixture.artifact_path);
  const physicalBytes = artifact.byteLength;
  const physicalSha = sha256(artifact);
  const detected = detectRaster(artifact);

  assert.ok(physicalBytes > 0, 'ARTIFACT_EMPTY');
  assert.ok(physicalBytes <= contract.artifact.max_bytes, 'ARTIFACT_TOO_LARGE');
  assertSha256(expected.sha256, 'fixture.expected.sha256');
  assertSha256(physicalSha, 'physical sha256');

  assert.equal(physicalSha, expected.sha256, 'HASH_MISMATCH');
  assert.equal(physicalBytes, expected.bytes, 'BYTE_COUNT_MISMATCH');
  assert.equal(detected.mime_type, expected.mime_type, 'MIME_MISMATCH');

  for (const field of contract.receipt.minimum_fields) {
    assert.notEqual(receipt[field], undefined, `RECEIPT_FIELD_MISSING:${field}`);
  }
  assert.equal(path.resolve(receipt.artifact_path), path.resolve(fixture.artifact_path), 'RECEIPT_PATH_MISMATCH');
  assert.equal(receipt.sha256, physicalSha, 'RECEIPT_HASH_MISMATCH');
  assert.equal(receipt.bytes, physicalBytes, 'RECEIPT_BYTES_MISMATCH');
  assert.equal(receipt.mime_type, detected.mime_type, 'RECEIPT_MIME_MISMATCH');

  assert.equal(probe.schema, expected.probe_schema, 'PROBE_SCHEMA_MISMATCH');
  assert.equal(probe.status, expected.probe_status, 'PROBE_STATUS_MISMATCH');
  assert.equal(probe.verdict, expected.probe_verdict, 'PROBE_VERDICT_MISMATCH');
  assert.equal(path.resolve(probe.artifact.path), path.resolve(fixture.artifact_path), 'PROBE_ARTIFACT_PATH_MISMATCH');
  assert.equal(path.resolve(probe.artifact.receipt_path), path.resolve(fixture.artifact_receipt_path), 'PROBE_RECEIPT_PATH_MISMATCH');
  assert.equal(probe.artifact.sha256, physicalSha, 'PROBE_HASH_MISMATCH');
  assert.equal(probe.artifact.bytes, physicalBytes, 'PROBE_BYTES_MISMATCH');
  assert.equal(probe.artifact.mime_type, detected.mime_type, 'PROBE_MIME_MISMATCH');

  return {
    sha256: physicalSha,
    bytes: physicalBytes,
    mime_type: detected.mime_type,
  };
}

function legacyEvidenceAvailable() {
  const fixture = readJson(FIXTURE_PATH);
  return [fixture.probe_receipt_path, fixture.artifact_path, fixture.artifact_receipt_path].every((filePath) => fs.existsSync(filePath));
}

function verifySuccessClaim(claim) {
  const successStates = new Set(readJson(CONTRACT_PATH).job_completion.success_states);
  if (!successStates.has(claim.status)) return true;
  if (!claim.artifact_path || !fs.existsSync(claim.artifact_path)) throw new Error('FALSE_SUCCESS:ARTIFACT_MISSING');
  if (!claim.receipt_path || !fs.existsSync(claim.receipt_path)) throw new Error('FALSE_SUCCESS:RECEIPT_MISSING');
  return true;
}

test('MX-012: physically present legacy Proxima baseline satisfies the independent MUXIA parity contract', { skip: !legacyEvidenceAvailable() && 'Windows legacy evidence is intentionally not migrated to Linux' }, () => {
  const fixture = readJson(FIXTURE_PATH);
  const result = verifyDurableEvidence(fixture);
  assert.equal(result.sha256, fixture.expected.sha256);
  assert.equal(result.bytes, fixture.expected.bytes);
  assert.equal(result.mime_type, fixture.expected.mime_type);
});

test('MX-012: a deliberately corrupted expected hash is rejected', { skip: !legacyEvidenceAvailable() && 'requires the sealed Windows legacy evidence' }, () => {
  const fixture = structuredClone(readJson(FIXTURE_PATH));
  fixture.expected.sha256 = '0'.repeat(64);
  assert.throws(() => verifyDurableEvidence(fixture), /HASH_MISMATCH/);
});

test('MX-012: a deliberately missing artifact path is rejected even if receipt text claims PASS', { skip: !legacyEvidenceAvailable() && 'requires the sealed Windows legacy evidence' }, () => {
  const fixture = structuredClone(readJson(FIXTURE_PATH));
  fixture.artifact_path = path.join(HERE, 'fixtures', 'definitely-missing-artifact.png');
  assert.throws(() => verifyDurableEvidence(fixture), /ARTIFACT_MISSING/);
});

test('MX-012: success text alone cannot create a completed job without durable evidence', () => {
  assert.throws(() => verifySuccessClaim({
    status: 'SUCCEEDED',
    artifact_path: path.join(HERE, 'fixtures', 'missing.png'),
    receipt_path: path.join(HERE, 'fixtures', 'missing.receipt.json'),
  }), /FALSE_SUCCESS:ARTIFACT_MISSING/);
});

test('MX-012: contract itself is Electron-independent and credential-free', () => {
  const raw = fs.readFileSync(CONTRACT_PATH, 'utf8');
  const contract = JSON.parse(raw);
  assert.deepEqual(contract.runtime_dependencies, []);
  assert.ok(contract.forbidden_runtime_dependencies.includes('electron'));
  assert.equal(contract.security.browser_session_secrets_are_out_of_scope, true);
  assert.equal(contract.security.credential_values_must_not_be_read_for_parity, true);
});
