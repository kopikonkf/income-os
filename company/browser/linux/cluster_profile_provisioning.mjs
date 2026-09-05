import fs from 'node:fs';
import path from 'node:path';

export const CLUSTER_PROVISIONING_STATES = Object.freeze([
  'PROVISIONED_EMPTY',
  'BROKER_PROOF_RUNNING',
  'WAITING_FOUNDER_AUTH',
  'AUTH_HANDOFF_VISIBLE_NO_CDP',
  'AUTH_HANDOFF_CLOSED',
  'BROKER_VERIFYING',
  'READY',
  'FAILED',
  'ROLLED_BACK',
]);

const TRANSITIONS = Object.freeze({
  PROVISIONED_EMPTY: new Set(['BROKER_PROOF_RUNNING', 'WAITING_FOUNDER_AUTH', 'FAILED', 'ROLLED_BACK']),
  BROKER_PROOF_RUNNING: new Set(['WAITING_FOUNDER_AUTH', 'FAILED']),
  WAITING_FOUNDER_AUTH: new Set(['AUTH_HANDOFF_VISIBLE_NO_CDP', 'FAILED', 'ROLLED_BACK']),
  AUTH_HANDOFF_VISIBLE_NO_CDP: new Set(['AUTH_HANDOFF_CLOSED', 'FAILED']),
  AUTH_HANDOFF_CLOSED: new Set(['BROKER_VERIFYING', 'FAILED']),
  BROKER_VERIFYING: new Set(['READY', 'WAITING_FOUNDER_AUTH', 'FAILED']),
  READY: new Set(['FAILED']),
  FAILED: new Set(['ROLLED_BACK']),
  ROLLED_BACK: new Set(),
});

const SAFE_AUTO_ROLLBACK_STATES = new Set(['PROVISIONED_EMPTY', 'WAITING_FOUNDER_AUTH', 'FAILED']);

function assertId(value, label) {
  if (typeof value !== 'string' || !/^[a-z0-9][a-z0-9._-]{1,80}$/.test(value)) throw new Error(`E_${label}_ID`);
}

function assertAbsoluteSafeRoot(value) {
  if (typeof value !== 'string' || !path.isAbsolute(value)) throw new Error('E_CLUSTER_ROOT_ABSOLUTE');
  const resolved = path.resolve(value);
  if (resolved === path.parse(resolved).root || resolved.length < path.parse(resolved).root.length + 8) throw new Error('E_CLUSTER_ROOT_TOO_BROAD');
  return resolved;
}

function nearestExistingAncestor(target) {
  let current = path.resolve(target);
  while (!fs.existsSync(current)) {
    const parent = path.dirname(current);
    if (parent === current) return current;
    current = parent;
  }
  return current;
}

function assertNoSymlinkOnExistingPath(target) {
  const resolved = path.resolve(target);
  const existing = nearestExistingAncestor(resolved);
  const root = path.parse(existing).root;
  const parts = path.relative(root, existing).split(path.sep).filter(Boolean);
  let current = root;
  for (const part of parts) {
    current = path.join(current, part);
    const stat = fs.lstatSync(current);
    if (stat.isSymbolicLink()) throw new Error(`E_CLUSTER_PATH_SYMLINK:${current}`);
  }
}

function writeJsonAtomic(file, value, mode = 0o640) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o750 });
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', mode });
  fs.renameSync(tmp, file);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function assertNoSecretFields(value, prefix = '') {
  if (!value || typeof value !== 'object') return;
  const forbidden = /(cookie|token|password|secret|credential|authorization|oauth.*code|session.*value)/i;
  for (const [key, child] of Object.entries(value)) {
    const qualified = prefix ? `${prefix}.${key}` : key;
    if (forbidden.test(key) && child !== false && child !== null) throw new Error(`E_SECRET_FIELD_FORBIDDEN:${qualified}`);
    assertNoSecretFields(child, qualified);
  }
}

function expectedOwner() {
  return {
    uid: typeof process.getuid === 'function' ? process.getuid() : null,
    gid: typeof process.getgid === 'function' ? process.getgid() : null,
  };
}

function assertOwnedDirectory(dir, { uid, gid } = expectedOwner()) {
  const st = fs.lstatSync(dir);
  if (!st.isDirectory() || st.isSymbolicLink()) throw new Error(`E_PROFILE_PATH_NOT_DIRECTORY:${dir}`);
  if (uid !== null && st.uid !== uid) throw new Error(`E_PROFILE_OWNER_UID:${dir}`);
  if (gid !== null && st.gid !== gid) throw new Error(`E_PROFILE_OWNER_GID:${dir}`);
  if ((st.mode & 0o022) !== 0) throw new Error(`E_PROFILE_WRITABLE_BY_GROUP_OR_WORLD:${dir}`);
  return { uid: st.uid, gid: st.gid, mode: st.mode & 0o777 };
}

export function validateClusterProvisioningContract(contract) {
  if (!contract || contract.schema !== 'die.factory-asset.cluster-provisioning-contract.v1') throw new Error('E_CLUSTER_PROVISIONING_CONTRACT_SCHEMA');
  const c = contract.cluster_b;
  if (!c) throw new Error('E_CLUSTER_B_CONTRACT_MISSING');
  assertId(c.cluster_id, 'CLUSTER');
  assertId(c.profile_id, 'PROFILE');
  if (c.cluster_id !== 'cluster-b') throw new Error('E_CLUSTER_B_ID');
  if (c.runtime_owner !== 'MUXIA') throw new Error('E_CLUSTER_RUNTIME_OWNER');
  if (c.browser_owner_model !== 'SINGLE_LONG_LIVED_CHROMIUM_PROCESS') throw new Error('E_CLUSTER_BROWSER_OWNER_MODEL');
  if (c.max_tabs !== 8) throw new Error('E_CLUSTER_TAB_CEILING');
  if (c.profile_secret_copy_allowed !== false || c.credential_cookie_token_export_allowed !== false) throw new Error('E_CLUSTER_SECRET_COPY_POLICY');
  if (c.auth_handoff !== 'VISIBLE_NO_CDP_PRE_DISPATCH_THEN_CLOSE_PROFILE_OWNER_BEFORE_BROKER_START') throw new Error('E_CLUSTER_AUTH_HANDOFF');
  if (c.initial_activation_state !== 'WAITING_FOUNDER_AUTH') throw new Error('E_CLUSTER_INITIAL_ACTIVATION');
  if (!Array.isArray(contract.lifecycle_states) || !CLUSTER_PROVISIONING_STATES.every((x) => contract.lifecycle_states.includes(x))) throw new Error('E_CLUSTER_LIFECYCLE_STATES');
  assertNoSecretFields(contract);
  return c;
}

export function resolveClusterProvisioningPaths(contract, clusterRootOverride = null) {
  const c = validateClusterProvisioningContract(contract);
  const clusterRoot = assertAbsoluteSafeRoot(clusterRootOverride || c.target_cluster_root);
  const profileDir = path.resolve(clusterRoot, c.profile_relative_dir);
  if (!profileDir.startsWith(`${clusterRoot}${path.sep}`)) throw new Error('E_PROFILE_PATH_OUTSIDE_CLUSTER_ROOT');
  return {
    cluster_root: clusterRoot,
    profile_dir: profileDir,
    state_dir: path.join(clusterRoot, 'state'),
    lock_dir: path.join(clusterRoot, 'locks'),
    provisioning_state_file: path.join(clusterRoot, 'state', 'provisioning.json'),
    broker_state_file: path.join(clusterRoot, 'state', 'broker.json'),
    broker_lock_file: path.join(clusterRoot, 'locks', 'broker.lock'),
  };
}

export function loadClusterProvisioningState(stateFile) {
  const state = readJson(stateFile);
  if (state.schema !== 'die.factory-asset.cluster-provisioning-state.v1') throw new Error('E_CLUSTER_PROVISIONING_STATE_SCHEMA');
  if (!CLUSTER_PROVISIONING_STATES.includes(state.state)) throw new Error('E_CLUSTER_PROVISIONING_STATE');
  assertNoSecretFields(state);
  return state;
}

export function assertProfilePathOwnership(paths, owner = expectedOwner()) {
  const cluster = assertOwnedDirectory(paths.cluster_root, owner);
  const profile = assertOwnedDirectory(paths.profile_dir, owner);
  const state = assertOwnedDirectory(paths.state_dir, owner);
  const locks = assertOwnedDirectory(paths.lock_dir, owner);
  return { cluster, profile, state, locks };
}

export function provisionFreshClusterProfile({ contract, clusterRootOverride = null, now = new Date().toISOString() }) {
  const c = validateClusterProvisioningContract(contract);
  const paths = resolveClusterProvisioningPaths(contract, clusterRootOverride);
  assertNoSymlinkOnExistingPath(paths.cluster_root);
  if (fs.existsSync(paths.cluster_root)) throw new Error('E_CLUSTER_ROOT_ALREADY_EXISTS');

  let created = false;
  try {
    fs.mkdirSync(paths.cluster_root, { recursive: false, mode: 0o750 });
    created = true;
    fs.mkdirSync(paths.profile_dir, { recursive: false, mode: 0o700 });
    fs.mkdirSync(paths.state_dir, { recursive: false, mode: 0o750 });
    fs.mkdirSync(paths.lock_dir, { recursive: false, mode: 0o750 });
    if (fs.readdirSync(paths.profile_dir).length !== 0) throw new Error('E_PROFILE_NOT_EMPTY_AFTER_CREATE');
    const ownership = assertProfilePathOwnership(paths);
    const record = {
      schema: 'die.factory-asset.cluster-provisioning-state.v1',
      cluster_id: c.cluster_id,
      profile_id: c.profile_id,
      state: 'PROVISIONED_EMPTY',
      cluster_root: paths.cluster_root,
      profile_dir: paths.profile_dir,
      browser_owner_model: c.browser_owner_model,
      runtime_owner: c.runtime_owner,
      max_tabs: c.max_tabs,
      created_at: now,
      updated_at: now,
      profile_initial_entries: 0,
      fresh_profile_created: true,
      source_profile_supplied: false,
      source_profile_read: false,
      inherited_session_material: false,
      auth_handoff_started: false,
      broker_proof_started: false,
      credential_values_read: false,
      cookies_or_tokens_read: false,
      ownership,
    };
    assertNoSecretFields(record);
    writeJsonAtomic(paths.provisioning_state_file, record);
    return { contract: c, paths, state: loadClusterProvisioningState(paths.provisioning_state_file) };
  } catch (error) {
    if (created) fs.rmSync(paths.cluster_root, { recursive: true, force: true });
    throw error;
  }
}

export function transitionClusterProvisioning({ stateFile, nextState, patch = {}, now = new Date().toISOString() }) {
  if (!CLUSTER_PROVISIONING_STATES.includes(nextState)) throw new Error('E_CLUSTER_PROVISIONING_NEXT_STATE');
  const current = loadClusterProvisioningState(stateFile);
  if (!TRANSITIONS[current.state]?.has(nextState)) throw new Error(`E_CLUSTER_PROVISIONING_TRANSITION:${current.state}:${nextState}`);
  const next = { ...current, ...patch, state: nextState, updated_at: now };
  if (nextState === 'AUTH_HANDOFF_VISIBLE_NO_CDP') next.auth_handoff_started = true;
  if (nextState === 'BROKER_PROOF_RUNNING') next.broker_proof_started = true;
  assertNoSecretFields(next);
  writeJsonAtomic(stateFile, next);
  return loadClusterProvisioningState(stateFile);
}

export function markWaitingFounderAuth({ stateFile, now = new Date().toISOString() }) {
  const current = loadClusterProvisioningState(stateFile);
  if (current.state === 'WAITING_FOUNDER_AUTH') return current;
  return transitionClusterProvisioning({ stateFile, nextState: 'WAITING_FOUNDER_AUTH', now });
}

export function rollbackClusterProvisioning({ stateFile, reason = 'BOUNDED_ROLLBACK' }) {
  const current = loadClusterProvisioningState(stateFile);
  if (current.auth_handoff_started) throw new Error('E_ROLLBACK_AUTH_MATERIAL_MAY_EXIST');
  if (!SAFE_AUTO_ROLLBACK_STATES.has(current.state)) throw new Error(`E_ROLLBACK_STATE:${current.state}`);
  const clusterRoot = assertAbsoluteSafeRoot(current.cluster_root);
  const lockFile = path.join(clusterRoot, 'locks', 'broker.lock');
  if (fs.existsSync(lockFile)) throw new Error('E_ROLLBACK_BROKER_LOCK_ACTIVE');
  const tombstone = {
    schema: 'die.factory-asset.cluster-provisioning-rollback.v1',
    cluster_id: current.cluster_id,
    profile_id: current.profile_id,
    previous_state: current.state,
    next_state: 'ROLLED_BACK',
    reason,
    auth_handoff_started: false,
    source_profile_read: false,
    inherited_session_material: false,
    credential_values_read: false,
    cookies_or_tokens_read: false,
  };
  fs.rmSync(clusterRoot, { recursive: true, force: true });
  return tombstone;
}
