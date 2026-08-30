#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { resolveMuxiaPaths } from '../dist/core/paths.js';
import {
  MX062_MIN_DURATION_MS,
  MX062_SAMPLE_INTERVAL_MS,
  appendSoakSample,
  finalizeSoak,
  runSyntheticSoakProbe,
  verifySoakChain,
} from '../dist/core/soak-runner.js';

function arg(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

const root = arg('--root');
const receiptPath = arg('--receipt');
if (!root || !receiptPath) {
  console.error('MX062_USAGE_ERROR');
  process.exit(2);
}
const resolvedRoot = path.resolve(root);
if (!path.basename(resolvedRoot).startsWith('mx062-soak-')) {
  console.error('MX062_ISOLATED_ROOT_REQUIRED');
  process.exit(2);
}
if (process.env.MUXIA_ROOT && path.resolve(process.env.MUXIA_ROOT) === resolvedRoot) {
  console.error('MX062_PRODUCTION_ROOT_FORBIDDEN');
  process.exit(2);
}

const paths = resolveMuxiaPaths({ root: resolvedRoot });
const ledgerPath = path.join(resolvedRoot, 'mx062-soak-ledger.jsonl');
fs.mkdirSync(resolvedRoot, { recursive: true });

function loadLedger() {
  if (!fs.existsSync(ledgerPath)) return [];
  const text = fs.readFileSync(ledgerPath, 'utf8').trim();
  if (!text) return [];
  const rows = text.split(/\r?\n/).map((line) => JSON.parse(line));
  if (!verifySoakChain(rows)) throw new Error('MX062_CHAIN_TAMPER');
  return rows;
}

function appendDurable(sample) {
  const fd = fs.openSync(ledgerPath, 'a', 0o600);
  try {
    fs.writeSync(fd, `${JSON.stringify(sample)}\n`, undefined, 'utf8');
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
}

function writeReceipt(receipt) {
  const output = path.resolve(receiptPath);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  const temporary = `${output}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(receipt, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
  fs.renameSync(temporary, output);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let samples;
try {
  samples = loadLedger();
} catch {
  console.error('MX062_CHAIN_TAMPER');
  process.exit(4);
}

const initialWallClockMs = samples.length
  ? Date.parse(samples[0].observedAt) - samples[0].elapsedMs
  : Date.now();

console.log(JSON.stringify({
  event: 'MX062_SOAK_STARTED_OR_RESUMED',
  minimumElapsedMs: MX062_MIN_DURATION_MS,
  sampleIntervalMs: MX062_SAMPLE_INTERVAL_MS,
  existingSamples: samples.length,
  isolatedRootId: path.basename(resolvedRoot),
}));

for (;;) {
  const nowMs = Date.now();
  const observedAt = new Date(nowMs).toISOString();
  const elapsedMs = nowMs - initialWallClockMs;
  let checks;
  try {
    checks = runSyntheticSoakProbe(paths, String(samples.length).padStart(6, '0'), observedAt);
  } catch {
    checks = {
      profileCorruption: 1,
      credentialLeakage: 0,
      duplicateOwnership: 0,
      recoveryMismatch: 1,
      artifactMismatch: 1,
      clockRollback: 0,
      chainTamper: 0,
    };
  }

  let sample;
  try {
    sample = appendSoakSample(samples, {
      observedAt,
      elapsedMs,
      checks,
      rssBytes: process.memoryUsage().rss,
    });
  } catch (error) {
    const code = error instanceof Error && error.message === 'MX062_CLOCK_ROLLBACK'
      ? 'MX062_CLOCK_ROLLBACK'
      : 'MX062_SAMPLE_REJECTED';
    console.error(code);
    process.exit(4);
  }
  appendDurable(sample);
  samples.push(sample);

  if (elapsedMs >= MX062_MIN_DURATION_MS) {
    let receipt;
    try {
      receipt = finalizeSoak(samples);
    } catch (error) {
      console.error(error instanceof Error ? error.message : 'MX062_FINALIZE_FAILED');
      process.exit(4);
    }
    writeReceipt(receipt);
    console.log(JSON.stringify({ event: 'MX062_SOAK_COMPLETE', status: receipt.status, samples: receipt.samples, coverage: receipt.coverage }));
    process.exit(receipt.status === 'PASS' ? 0 : 3);
  }

  await sleep(MX062_SAMPLE_INTERVAL_MS);
}
