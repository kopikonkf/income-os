import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { resolveMuxiaPaths } from '../../dist/core/paths.js';
import {
  MX062_MIN_COVERAGE,
  MX062_MIN_DURATION_MS,
  MX062_SAMPLE_INTERVAL_MS,
  appendSoakSample,
  finalizeSoak,
  runSyntheticSoakProbe,
  verifySoakChain,
} from '../../dist/core/soak-runner.js';

const ZERO = {
  profileCorruption: 0,
  credentialLeakage: 0,
  duplicateOwnership: 0,
  recoveryMismatch: 0,
  artifactMismatch: 0,
  clockRollback: 0,
  chainTamper: 0,
};

function sampleSeries(count, elapsedMs = MX062_MIN_DURATION_MS) {
  const base = Date.parse('2026-08-30T00:00:00.000Z');
  const rows = [];
  for (let index = 0; index < count; index += 1) {
    const elapsed = count === 1 ? 0 : Math.round((elapsedMs * index) / (count - 1));
    rows.push(appendSoakSample(rows, {
      observedAt: new Date(base + elapsed).toISOString(),
      elapsedMs: elapsed,
      checks: ZERO,
      rssBytes: 1000 + index,
    }));
  }
  return rows;
}

test('MX-062 runner constants cannot satisfy less than real 24h and pin one-minute sampling', () => {
  assert.equal(MX062_MIN_DURATION_MS, 86_400_000);
  assert.equal(MX062_SAMPLE_INTERVAL_MS, 60_000);
  assert.equal(MX062_MIN_COVERAGE, 0.95);
  const rows = sampleSeries(2, MX062_MIN_DURATION_MS - 1);
  assert.throws(() => finalizeSoak(rows), /MX062_MINIMUM_24H_NOT_MET/);
});

test('MX-062 sample chain rejects clock rollback and detects tamper', () => {
  const rows = sampleSeries(3, 120_000);
  assert.equal(verifySoakChain(rows), true);
  assert.throws(() => appendSoakSample(rows, {
    observedAt: '2026-08-29T23:59:59.000Z',
    elapsedMs: 121_000,
    checks: ZERO,
  }), /MX062_CLOCK_ROLLBACK/);
  const tampered = structuredClone(rows);
  tampered[1].rssBytes += 1;
  assert.equal(verifySoakChain(tampered), false);
  assert.throws(() => finalizeSoak(tampered), /MX062_CHAIN_TAMPER/);
});

test('MX-062 finalizer requires >=95% sample coverage and zero failure counters', () => {
  const expected = Math.floor(MX062_MIN_DURATION_MS / MX062_SAMPLE_INTERVAL_MS) + 1;
  const passCount = Math.ceil(expected * MX062_MIN_COVERAGE);
  const passing = sampleSeries(passCount);
  const receipt = finalizeSoak(passing);
  assert.equal(receipt.status, 'PASS');
  assert.ok(receipt.coverage >= 0.95);
  assert.equal(receipt.failures.credentialLeakage, 0);
  assert.equal(receipt.authorityBoundary.providerInvoked, false);
  assert.equal(receipt.authorityBoundary.credentialsRead, false);

  const sparse = sampleSeries(passCount - 1);
  assert.equal(finalizeSoak(sparse).status, 'FAIL');

  const failed = structuredClone(passing);
  failed[failed.length - 1] = appendSoakSample(failed.slice(0, -1), {
    observedAt: failed.at(-1).observedAt,
    elapsedMs: failed.at(-1).elapsedMs,
    checks: { ...ZERO, recoveryMismatch: 1 },
    rssBytes: failed.at(-1).rssBytes,
  });
  assert.equal(finalizeSoak(failed).status, 'FAIL');
  assert.equal(finalizeSoak(failed).failures.recoveryMismatch, 1);
});

test('MX-062 synthetic probe exercises registry, duplicate lease, crash recovery and artifact durability with zero failures', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'mx062-soak-test-'));
  try {
    const paths = resolveMuxiaPaths({ root });
    const counters = runSyntheticSoakProbe(paths, '000001', '2026-08-30T00:00:00.000Z');
    assert.deepEqual(counters, ZERO);
    const stateText = fs.readdirSync(paths.state, { recursive: true })
      .filter((entry) => typeof entry === 'string' && entry.endsWith('.json'))
      .map((entry) => fs.readFileSync(path.join(paths.state, entry), 'utf8'))
      .join('\n');
    assert.doesNotMatch(stateText, /bearer\s|password|cookie|authorization/i);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('MX-062 CLI exposes no duration-shortening flag and forbids production root reuse', () => {
  const script = fs.readFileSync(new URL('../../scripts/mx062-soak.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(script, /--duration|--hours|--minutes|--interval/);
  assert.match(script, /MX062_PRODUCTION_ROOT_FORBIDDEN/);
  assert.match(script, /MX062_MIN_DURATION_MS/);
  assert.doesNotMatch(script, /providers\/|playwright|chatgpt/i);
});


test('MX-062 Linux service is restart-safe, source-readonly, and isolated from production MUXIA state', () => {
  const unit = fs.readFileSync(new URL('../../config/linux/systemd/muxia-mx062-soak@.service', import.meta.url), 'utf8');
  const installer = fs.readFileSync(new URL('../../scripts/linux/mx062-install-soak.sh', import.meta.url), 'utf8');
  assert.match(unit, /Restart=on-failure/);
  assert.match(unit, /ReadOnlyPaths=\/srv\/die/);
  assert.match(unit, /ReadWritePaths=\/var\/lib\/muxia-soak/);
  assert.match(unit, /--root \/var\/lib\/muxia-soak\/mx062-soak-v1/);
  assert.doesNotMatch(unit, /--root \/var\/lib\/muxia(?:\s|$)/);
  assert.match(installer, /MX062_NOT_STARTED:explicit_start_required/);
  assert.match(installer, /NODE_24_LTS_REQUIRED/);
  assert.doesNotMatch(installer, /systemctl start/);
});
