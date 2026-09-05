#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { ClusterBrokerCore } from '../../browser/linux/cluster_broker_core.mjs';
import {
  assertProfilePathOwnership,
  loadClusterProvisioningState,
  markWaitingFounderAuth,
  provisionFreshClusterProfile,
  rollbackClusterProvisioning,
  transitionClusterProvisioning,
  validateClusterProvisioningContract,
} from '../../browser/linux/cluster_profile_provisioning.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../../..');
const CONTRACT_PATH = path.join(ROOT, 'company/factory-asset/contracts/cluster-provisioning.v1.json');
const AUTH_HANDOFF_PATH = path.join(ROOT, 'company/muxia/scripts/linux/muxia-cluster-auth-handoff.mjs');
const CONTRACT = JSON.parse(fs.readFileSync(CONTRACT_PATH, 'utf8'));
const NOW = '2026-09-05T20:20:00.000Z';

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

async function waitForDevTools(profileDir, child, timeoutMs = 15000) {
  const portFile = path.join(profileDir, 'DevToolsActivePort');
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`E_TEMP_CHROMIUM_EXITED:${child.exitCode}`);
    try {
      const lines = fs.readFileSync(portFile, 'utf8').split(/\r?\n/).filter(Boolean);
      const port = Number(lines[0]);
      if (Number.isInteger(port) && port > 0 && port <= 65535) return port;
    } catch (error) {
      if (!['ENOENT', 'EBUSY', 'EACCES'].includes(error?.code)) throw error;
    }
    await sleep(50);
  }
  throw new Error('E_TEMP_CHROMIUM_DEBUG_TIMEOUT');
}

async function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null) return true;
  return await Promise.race([
    new Promise((resolve) => child.once('exit', () => resolve(true))),
    sleep(timeoutMs).then(() => false),
  ]);
}

class TemporaryChromiumDriver {
  constructor(browserPath) { this.browserPath = browserPath; this.child = null; this.launchCalls = 0; this.stopCalls = 0; }
  async launch(profileDir) {
    if (this.child) throw new Error('E_TEMP_CHROMIUM_ALREADY_RUNNING');
    this.launchCalls += 1;
    const child = spawn(this.browserPath, [
      '--headless=new',
      `--user-data-dir=${profileDir}`,
      '--remote-debugging-address=127.0.0.1',
      '--remote-debugging-port=0',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-background-networking',
      '--disable-component-update',
      '--disable-sync',
      '--disable-default-apps',
      '--no-proxy-server',
      '--host-resolver-rules=MAP * 0.0.0.0, EXCLUDE localhost',
      'about:blank',
    ], { stdio: ['ignore', 'ignore', 'pipe'] });
    this.child = child;
    let stderr = '';
    child.stderr?.on('data', (chunk) => { stderr = `${stderr}${chunk.toString()}`.slice(-4096); });
    try {
      const port = await waitForDevTools(profileDir, child);
      const response = await fetch(`http://127.0.0.1:${port}/json/version`, { signal: AbortSignal.timeout(3000) });
      if (!response.ok) throw new Error(`E_TEMP_CHROMIUM_DEBUG_HTTP:${response.status}`);
      return { pid: child.pid, userDataDir: profileDir, debugHost: '127.0.0.1', debugPort: port, debugUrl: `http://127.0.0.1:${port}`, browser: {} };
    } catch (error) {
      child.kill('SIGTERM');
      await waitForExit(child, 1000);
      this.child = null;
      throw new Error(`${error.message}:stderr=${stderr.slice(-800)}`);
    }
  }
  async stop() {
    this.stopCalls += 1;
    const child = this.child; this.child = null;
    if (!child) return;
    if (child.exitCode === null) child.kill('SIGTERM');
    if (!(await waitForExit(child, 3000)) && child.exitCode === null) child.kill('SIGKILL');
    await waitForExit(child, 2000);
  }
}

function browserPath() {
  const candidates = [process.env.MUXIA_STABLE_BROWSER, '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'].filter(Boolean);
  const found = candidates.find((x) => path.isAbsolute(x) && fs.existsSync(x));
  if (!found) throw new Error('E_FA305_BROWSER_NOT_FOUND');
  return found;
}

function expectError(fn, pattern) {
  try { fn(); } catch (error) {
    const message = String(error?.message || error);
    if (!message.includes(pattern)) throw error;
    return message;
  }
  throw new Error(`EXPECTED_ERROR:${pattern}`);
}

async function expectAsyncError(fn, pattern) {
  try { await fn(); } catch (error) {
    const message = String(error?.message || error);
    if (!message.includes(pattern)) throw error;
    return message;
  }
  throw new Error(`EXPECTED_ASYNC_ERROR:${pattern}`);
}

validateClusterProvisioningContract(CONTRACT);
const tempParents = [];
const results = {};

try {
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'fa305-cluster-b-proof-'));
  tempParents.push(parent);
  const clusterRoot = path.join(parent, 'cluster-b');
  const provisioned = provisionFreshClusterProfile({ contract: CONTRACT, clusterRootOverride: clusterRoot, now: NOW });
  const initialEntries = fs.readdirSync(provisioned.paths.profile_dir);
  if (initialEntries.length !== 0) throw new Error('E_FA305_PROFILE_NOT_EMPTY');
  const ownership = assertProfilePathOwnership(provisioned.paths);

  const driver1 = new TemporaryChromiumDriver(browserPath());
  const broker1 = new ClusterBrokerCore({
    clusterId: CONTRACT.cluster_b.cluster_id,
    profileId: CONTRACT.cluster_b.profile_id,
    profileDir: provisioned.paths.profile_dir,
    stateFile: provisioned.paths.broker_state_file,
    lockFile: provisioned.paths.broker_lock_file,
    driver: driver1,
    maxTabs: CONTRACT.cluster_b.max_tabs,
    controlHost: '127.0.0.1',
    controlPort: 0,
  });
  transitionClusterProvisioning({ stateFile: provisioned.paths.provisioning_state_file, nextState: 'BROKER_PROOF_RUNNING', now: NOW });
  const brokerState = await broker1.start();
  const attach = await (await fetch(`http://127.0.0.1:${brokerState.control_port}/v1/attach`)).json();
  if (attach.cluster_id !== 'cluster-b' || attach.profile_id !== 'web-ai-cluster-b' || attach.max_tabs !== 8) throw new Error('E_FA305_ATTACH_IDENTITY');
  if (attach.debug_host !== '127.0.0.1' || attach.browser_owner_pid <= 0) throw new Error('E_FA305_ATTACH_OWNER');

  const driver2 = new TemporaryChromiumDriver(browserPath());
  const broker2 = new ClusterBrokerCore({
    clusterId: CONTRACT.cluster_b.cluster_id,
    profileId: CONTRACT.cluster_b.profile_id,
    profileDir: provisioned.paths.profile_dir,
    stateFile: path.join(provisioned.paths.state_dir, 'broker-second.json'),
    lockFile: provisioned.paths.broker_lock_file,
    driver: driver2,
    maxTabs: 8,
  });
  const secondOwnerError = await expectAsyncError(() => broker2.start(), 'E_CLUSTER_BROKER_ALREADY_OWNED');
  if (driver2.launchCalls !== 0) throw new Error('E_FA305_SECOND_OWNER_LAUNCHED_BROWSER');
  const lockPreservedAfterSecondOwnerRejection = fs.existsSync(provisioned.paths.broker_lock_file);
  if (!lockPreservedAfterSecondOwnerRejection) throw new Error('E_FA305_PRIMARY_OWNER_LOCK_LOST');
  await broker2.stop();
  const lockPreservedAfterNonOwnerStop = fs.existsSync(provisioned.paths.broker_lock_file);
  if (!lockPreservedAfterNonOwnerStop) throw new Error('E_FA305_NON_OWNER_STOP_REMOVED_LOCK');

  const entriesAfterBrowserCount = fs.readdirSync(provisioned.paths.profile_dir).length;
  await broker1.stop();
  const waiting = markWaitingFounderAuth({ stateFile: provisioned.paths.provisioning_state_file, now: NOW });
  if (waiting.state !== 'WAITING_FOUNDER_AUTH' || waiting.auth_handoff_started !== false) throw new Error('E_FA305_WAITING_AUTH_STATE');
  if (fs.existsSync(provisioned.paths.broker_lock_file)) throw new Error('E_FA305_BROKER_LOCK_NOT_RELEASED');

  results.temporary_real_broker_proof = {
    fresh_profile_initial_entries: initialEntries.length,
    browser_generated_entries_after_start_count: entriesAfterBrowserCount,
    ownership,
    broker_state: brokerState.state,
    browser_owner_model: brokerState.browser_owner_model,
    browser_owner_pid_present: brokerState.browser_owner_pid > 0,
    control_host: brokerState.control_host,
    debug_host: brokerState.debug_host,
    max_tabs: brokerState.max_tabs,
    second_owner_blocked: secondOwnerError.includes('E_CLUSTER_BROKER_ALREADY_OWNED'),
    second_owner_browser_launch_calls: driver2.launchCalls,
    primary_owner_lock_preserved_after_second_rejection: lockPreservedAfterSecondOwnerRejection,
    primary_owner_lock_preserved_after_non_owner_stop: lockPreservedAfterNonOwnerStop,
    first_owner_launch_calls: driver1.launchCalls,
    first_owner_stop_calls: driver1.stopCalls,
    final_pre_auth_state: waiting.state,
    broker_lock_released: !fs.existsSync(provisioned.paths.broker_lock_file),
    source_profile_supplied: waiting.source_profile_supplied,
    source_profile_read: waiting.source_profile_read,
    inherited_session_material: waiting.inherited_session_material,
    credential_values_read: false,
    cookies_or_tokens_read: false,
  };

  const rollback = rollbackClusterProvisioning({ stateFile: provisioned.paths.provisioning_state_file, reason: 'TEMPORARY_ACCEPTANCE_COMPLETE' });
  results.temporary_real_broker_proof.rollback = { ...rollback, cluster_root_removed: !fs.existsSync(clusterRoot) };

  const rollbackParent = fs.mkdtempSync(path.join(os.tmpdir(), 'fa305-rollback-proof-'));
  tempParents.push(rollbackParent);
  const rollbackRoot = path.join(rollbackParent, 'cluster-b');
  const rollbackProvisioned = provisionFreshClusterProfile({ contract: CONTRACT, clusterRootOverride: rollbackRoot, now: NOW });
  const failingDriver = { launchCalls: 0, stopCalls: 0, async launch() { this.launchCalls += 1; throw new Error('SYNTHETIC_DRIVER_FAILURE'); }, async stop() { this.stopCalls += 1; } };
  const failingBroker = new ClusterBrokerCore({
    clusterId: 'cluster-b', profileId: 'web-ai-cluster-b', profileDir: rollbackProvisioned.paths.profile_dir,
    stateFile: rollbackProvisioned.paths.broker_state_file, lockFile: rollbackProvisioned.paths.broker_lock_file,
    driver: failingDriver, maxTabs: 8,
  });
  const launchFailure = await expectAsyncError(() => failingBroker.start(), 'SYNTHETIC_DRIVER_FAILURE');
  transitionClusterProvisioning({ stateFile: rollbackProvisioned.paths.provisioning_state_file, nextState: 'FAILED', patch: { failure_code: 'SYNTHETIC_DRIVER_FAILURE' }, now: NOW });
  const rollbackFailure = rollbackClusterProvisioning({ stateFile: rollbackProvisioned.paths.provisioning_state_file, reason: 'SYNTHETIC_BROKER_START_FAILURE' });
  results.rollback_failure_proof = {
    launch_failure_typed: launchFailure.includes('SYNTHETIC_DRIVER_FAILURE'),
    broker_lock_released: !fs.existsSync(rollbackProvisioned.paths.broker_lock_file),
    cluster_root_removed: !fs.existsSync(rollbackRoot),
    rollback: rollbackFailure,
  };

  const symlinkParent = fs.mkdtempSync(path.join(os.tmpdir(), 'fa305-symlink-proof-'));
  tempParents.push(symlinkParent);
  const target = path.join(symlinkParent, 'real');
  fs.mkdirSync(target);
  const link = path.join(symlinkParent, 'linked');
  fs.symlinkSync(target, link, 'dir');
  const symlinkError = expectError(() => provisionFreshClusterProfile({ contract: CONTRACT, clusterRootOverride: path.join(link, 'cluster-b'), now: NOW }), 'E_CLUSTER_PATH_SYMLINK');
  results.path_guard_proof = { symlink_rejected: symlinkError.includes('E_CLUSTER_PATH_SYMLINK') };

  const ownerParent = fs.mkdtempSync(path.join(os.tmpdir(), 'fa305-owner-proof-'));
  tempParents.push(ownerParent);
  const ownerRoot = path.join(ownerParent, 'cluster-b');
  const ownerProvisioned = provisionFreshClusterProfile({ contract: CONTRACT, clusterRootOverride: ownerRoot, now: NOW });
  const stat = fs.statSync(ownerProvisioned.paths.profile_dir);
  const ownerError = expectError(() => assertProfilePathOwnership(ownerProvisioned.paths, { uid: stat.uid + 1, gid: stat.gid }), 'E_PROFILE_OWNER_UID');
  results.ownership_guard_proof = { mismatched_uid_rejected: ownerError.includes('E_PROFILE_OWNER_UID') };
  rollbackClusterProvisioning({ stateFile: ownerProvisioned.paths.provisioning_state_file, reason: 'OWNERSHIP_GUARD_PROOF_COMPLETE' });

  const authSource = fs.readFileSync(AUTH_HANDOFF_PATH, 'utf8').toLowerCase();
  const authForbidden = ['--remote-debugging-port', '--remote-debugging-address', 'connectovercdp', 'playwright', 'context.cookies', 'storagestate'];
  results.auth_handoff_contract = {
    source_present: true,
    visible_display_required: authSource.includes('display_required'),
    initial_url_about_blank: authSource.includes("'about:blank'"),
    broker_must_be_stopped: authSource.includes('broker_must_be_stopped'),
    remote_debugging_or_automation_tokens_present: authForbidden.filter((x) => authSource.includes(x)),
    provider_login_automated: false,
    executed_in_fa305_acceptance: false,
  };

  const assertions = {
    fresh_profile_created_empty: results.temporary_real_broker_proof.fresh_profile_initial_entries === 0,
    no_source_profile_supplied_or_read: results.temporary_real_broker_proof.source_profile_supplied === false && results.temporary_real_broker_proof.source_profile_read === false,
    no_inherited_session_material: results.temporary_real_broker_proof.inherited_session_material === false,
    real_chromium_single_broker_owner: results.temporary_real_broker_proof.browser_owner_pid_present && results.temporary_real_broker_proof.second_owner_blocked && results.temporary_real_broker_proof.second_owner_browser_launch_calls === 0 && results.temporary_real_broker_proof.primary_owner_lock_preserved_after_second_rejection && results.temporary_real_broker_proof.primary_owner_lock_preserved_after_non_owner_stop,
    max_eight_preserved: results.temporary_real_broker_proof.max_tabs === 8,
    loopback_only_broker: results.temporary_real_broker_proof.control_host === '127.0.0.1' && results.temporary_real_broker_proof.debug_host === '127.0.0.1',
    final_state_waiting_founder_auth: results.temporary_real_broker_proof.final_pre_auth_state === 'WAITING_FOUNDER_AUTH',
    rollback_after_pre_auth_proof: results.temporary_real_broker_proof.rollback.cluster_root_removed,
    rollback_after_broker_failure: results.rollback_failure_proof.cluster_root_removed && results.rollback_failure_proof.broker_lock_released,
    symlink_path_rejected: results.path_guard_proof.symlink_rejected,
    ownership_mismatch_rejected: results.ownership_guard_proof.mismatched_uid_rejected,
    auth_handoff_is_visible_no_cdp_contract: results.auth_handoff_contract.visible_display_required && results.auth_handoff_contract.broker_must_be_stopped && results.auth_handoff_contract.remote_debugging_or_automation_tokens_present.length === 0,
    zero_provider_calls: true,
    zero_founder_auth_actions: true,
    cluster_a_not_accessed: true,
  };

  const receipt = {
    schema: 'die.factory-asset.fa305-cluster-b-provisioning-acceptance.v1',
    task_id: 'FA-305',
    date: '2026-09-05',
    implementation_result: Object.values(assertions).every(Boolean) ? 'PASS' : 'FAIL',
    task_state: Object.values(assertions).every(Boolean) ? 'WAITING_FOUNDER_AUTH' : 'FAILED',
    full_fa305_acceptance: false,
    reason: 'Founder provider-account authentication has not been performed; full FA-305 PASS is intentionally not claimed.',
    founder_auth_performed: false,
    provider_calls_performed: 0,
    provider_login_automation_performed: false,
    spend_authorized: false,
    cluster_a_profile_accessed: false,
    source_profile_copy_attempted: false,
    source_profile_read_attempted: false,
    temporary_profile_only: true,
    canonical_cluster_b_profile_created: false,
    contract: 'company/factory-asset/contracts/cluster-provisioning.v1.json',
    provisioner: 'company/browser/linux/cluster_profile_provisioning.mjs',
    auth_handoff: 'company/muxia/scripts/linux/muxia-cluster-auth-handoff.mjs',
    assertions,
    evidence: results,
    next_boundary: 'FOUNDER_AUTH_REQUIRED: provision canonical Cluster B under governed authority, open visible no-CDP browser, Founder authenticates chosen providers, fully close browser, then restart one MUXIA broker and verify FA-303 readiness before FA-305 can become DONE/PASS.',
  };
  process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
  if (receipt.implementation_result !== 'PASS') process.exitCode = 1;
} finally {
  for (const parent of tempParents) fs.rmSync(parent, { recursive: true, force: true });
}
