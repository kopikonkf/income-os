import {createHash} from 'node:crypto';
import {existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import {tmpdir} from 'node:os';

const ROOT = dirname(new URL(import.meta.url).pathname.replace(/^\/(?:([A-Za-z]:))/, '$1'));
const CLI = join(ROOT, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');
const ENTRY = join(ROOT, 'src', 'index.jsx');
const COMPOSITION = 'ShoppingBagBounce';
const REMOTION_PACKAGE_VERSION = '4.0.520';
const CONTRACT = JSON.parse(readFileSync(join(ROOT, 'src', 'composition-contract.json'), 'utf8'));
const PRODUCER_VERSION = CONTRACT.renderer.renderer_version;
const JOB_ID = 'FA041-REMOTION-001';

const stable = (value) => {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
};

const sha256Buffer = (buffer) => createHash('sha256').update(buffer).digest('hex');
const COMPOSITION_SHA256 = sha256Buffer(Buffer.from(stable(CONTRACT), 'utf8'));
const IDEMPOTENCY_KEY = sha256Buffer(Buffer.from(stable({composition_sha256: COMPOSITION_SHA256, renderer: CONTRACT.renderer, video: CONTRACT.video, audio: CONTRACT.audio}), 'utf8'));
const sha256File = (path) => sha256Buffer(readFileSync(path));

const runCli = (args) => {
  const child = spawnSync(process.execPath, [CLI, ...args], {cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']});
  if (child.status !== 0) {
    throw new Error(`REMOTION_COMMAND_FAILED ${args.join(' ')}\n${child.stdout || ''}\n${child.stderr || ''}`);
  }
  return {stdout: child.stdout || '', stderr: child.stderr || ''};
};

const assertMagic = (mp4, png) => {
  const video = readFileSync(mp4);
  const preview = readFileSync(png);
  if (video.length < 12 || video.subarray(4, 8).toString('ascii') !== 'ftyp') throw new Error('MP4_MAGIC_INVALID');
  if (!preview.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) throw new Error('PNG_MAGIC_INVALID');
};

const render = ({outputDir, injectFailure = false}) => {
  const finalDir = resolve(outputDir);
  const parent = dirname(finalDir);
  mkdirSync(parent, {recursive: true});
  if (existsSync(finalDir)) throw new Error(`OUTPUT_DIR_EXISTS ${finalDir}`);
  const temp = mkdtempSync(join(parent, '.fa041-tmp-'));
  let finalized = false;
  try {
    writeFileSync(join(temp, 'temp-marker.txt'), 'FA-041 temporary render workspace\n');
    if (injectFailure) throw new Error('INJECTED_FAILURE_BEFORE_RENDER');
    runCli(['browser', 'ensure']);
    const mp4 = join(temp, 'master.mp4');
    const png = join(temp, 'preview.png');
    runCli(['render', ENTRY, COMPOSITION, mp4, '--codec=h264', '--pixel-format=yuv420p', '--image-format=png', '--muted', '--concurrency=1', '--log=warn']);
    runCli(['still', ENTRY, COMPOSITION, png, '--frame=90', '--log=warn']);
    assertMagic(mp4, png);
    rmSync(join(temp, 'temp-marker.txt'), {force: true});
    const masterBytes = readFileSync(mp4);
    const previewBytes = readFileSync(png);
    const master = {
      format: 'MP4',
      sha256: sha256Buffer(masterBytes),
      bytes: masterBytes.length,
      native_editable: true,
      generated_by_native_producer: true,
      conversion_from_raster: false,
      lineage_sha256_required: true,
    };
    const nativeReceipt = {
      schema: 'die.factory-asset.native-producer.v1', kind: 'RECEIPT', job_id: JOB_ID,
      idempotency_key: IDEMPOTENCY_KEY, producer_class: 'MOTION_RENDERER', producer_version: PRODUCER_VERSION,
      result: 'PASS', master,
    };
    nativeReceipt.deterministic_receipt_sha256 = sha256Buffer(Buffer.from(stable(nativeReceipt), 'utf8'));
    const receipt = {
      schema: 'die.factory-asset.remotion-fixture-result.v1',
      result: 'PASS',
      composition_id: COMPOSITION,
      renderer_package: `remotion@${REMOTION_PACKAGE_VERSION}`,
      render_flags: ['--codec=h264','--pixel-format=yuv420p','--image-format=png','--muted','--concurrency=1'],
      expected_contract: {duration_seconds: CONTRACT.duration_seconds, fps: CONTRACT.fps, frame_count: CONTRACT.frame_count, width: CONTRACT.canvas.width, height: CONTRACT.canvas.height, container: CONTRACT.video.container, codec: CONTRACT.video.codec, pixel_format: CONTRACT.video.pixel_format, audio_policy: CONTRACT.audio.policy, seed: CONTRACT.seed, renderer: CONTRACT.renderer},
      master_path: 'master.mp4', preview_path: 'preview.png', preview_frame: 90,
      master_sha256: master.sha256, master_bytes: master.bytes,
      preview_sha256: sha256Buffer(previewBytes), preview_bytes: previewBytes.length,
      native_receipt: nativeReceipt,
      temporary_workspace_finalized: true,
    };
    writeFileSync(join(temp, 'worker-receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`);
    renameSync(temp, finalDir);
    finalized = true;
    return {...receipt, output_dir: finalDir};
  } finally {
    if (!finalized && existsSync(temp)) rmSync(temp, {recursive: true, force: true});
  }
};

const selfTestCleanup = () => {
  const base = mkdtempSync(join(tmpdir(), 'fa041-cleanup-test-'));
  const target = join(base, 'final');
  let failed = false;
  try {
    render({outputDir: target, injectFailure: true});
  } catch (error) {
    failed = String(error).includes('INJECTED_FAILURE_BEFORE_RENDER');
  }
  const leftovers = existsSync(base) ? readdirSync(base) : [];
  rmSync(base, {recursive: true, force: true});
  if (!failed || leftovers.length !== 0 || existsSync(target)) throw new Error(`CLEANUP_SELF_TEST_FAILED failed=${failed} leftovers=${leftovers.join(',')}`);
  return {schema: 'die.factory-asset.remotion-cleanup-self-test.v1', result: 'PASS', injected_failure_observed: true, temporary_entries_after_failure: 0, partial_final_output: false};
};

const args = process.argv.slice(2);
if (args.includes('--self-test-cleanup')) {
  console.log(JSON.stringify(selfTestCleanup()));
} else {
  const idx = args.indexOf('--output-dir');
  if (idx < 0 || !args[idx + 1]) throw new Error('--output-dir is required');
  console.log(JSON.stringify(render({outputDir: args[idx + 1]})));
}
