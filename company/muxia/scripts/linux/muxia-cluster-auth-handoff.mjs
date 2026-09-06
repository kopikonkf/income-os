#!/usr/bin/env node
import fs from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';
import {
  assertProfilePathOwnership,
  loadClusterProvisioningState,
  transitionClusterProvisioning,
} from '../../../browser/linux/cluster_profile_provisioning.mjs';

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith('--')) throw new Error(`E_AUTH_HANDOFF_ARG:${key}`);
    const value = argv[++i];
    if (!value || value.startsWith('--')) throw new Error(`E_AUTH_HANDOFF_ARG_VALUE:${key}`);
    out[key.slice(2)] = value;
  }
  return out;
}

function resolveBrowser(explicit) {
  const candidates = [explicit, process.env.MUXIA_STABLE_BROWSER, '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'].filter(Boolean);
  for (const candidate of candidates) if (path.isAbsolute(candidate) && fs.existsSync(candidate)) return candidate;
  throw new Error('E_AUTH_HANDOFF_STABLE_BROWSER_NOT_FOUND');
}

async function waitChild(child) {
  return await new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', (code, signal) => resolve({ code, signal }));
  });
}

const args = parseArgs(process.argv.slice(2));
if (!args['state-file'] || !path.isAbsolute(args['state-file'])) throw new Error('E_AUTH_HANDOFF_STATE_FILE');
if (!process.env.DISPLAY) throw new Error('E_AUTH_HANDOFF_DISPLAY_REQUIRED');

const current = loadClusterProvisioningState(args['state-file']);
const resumeVisible = args['resume-visible'] === 'yes';
if (resumeVisible) {
  if (current.state !== 'AUTH_HANDOFF_VISIBLE_NO_CDP') throw new Error(`E_AUTH_HANDOFF_RESUME_STATE:${current.state}`);
} else if (current.state !== 'WAITING_FOUNDER_AUTH') {
  throw new Error(`E_AUTH_HANDOFF_STATE:${current.state}`);
}
const clusterRoot = path.resolve(current.cluster_root);
const paths = {
  cluster_root: clusterRoot,
  profile_dir: path.resolve(current.profile_dir),
  state_dir: path.join(clusterRoot, 'state'),
  lock_dir: path.join(clusterRoot, 'locks'),
};
assertProfilePathOwnership(paths);
const brokerLock = path.join(paths.lock_dir, 'broker.lock');
if (fs.existsSync(brokerLock)) throw new Error('E_AUTH_HANDOFF_BROKER_MUST_BE_STOPPED');

const browser = resolveBrowser(args.browser);
if (!resumeVisible) {
  transitionClusterProvisioning({
    stateFile: args['state-file'],
    nextState: 'AUTH_HANDOFF_VISIBLE_NO_CDP',
    patch: {
      auth_handoff_mode: 'VISIBLE_STABLE_BROWSER_NO_CDP',
      initial_url: 'about:blank',
      automation_attachment_used: false,
      credential_values_read: false,
      cookies_or_tokens_read: false,
    },
  });
}

const child = spawn(browser, [
  `--user-data-dir=${paths.profile_dir}`,
  '--no-first-run',
  '--no-default-browser-check',
  'about:blank',
], {
  stdio: 'inherit',
  env: process.env,
});

const result = await waitChild(child);
if (result.code === 0) {
  transitionClusterProvisioning({
    stateFile: args['state-file'],
    nextState: 'AUTH_HANDOFF_CLOSED',
    patch: {
      browser_exit_code: 0,
      browser_fully_closed: true,
      broker_restart_permitted: true,
      provider_login_automated: false,
      credential_values_read: false,
      cookies_or_tokens_read: false,
    },
  });
  process.stdout.write(`${JSON.stringify({ schema: 'die.muxia.cluster-auth-handoff.v1', status: 'CLOSED', resumed_visible_handoff: resumeVisible, browser_fully_closed: true, broker_restart_permitted: true, provider_login_automated: false, credential_values_read: false, cookies_or_tokens_read: false })}\n`);
} else {
  transitionClusterProvisioning({
    stateFile: args['state-file'],
    nextState: 'FAILED',
    patch: {
      failure_code: 'VISIBLE_BROWSER_EXITED_NONZERO',
      browser_exit_code: result.code,
      browser_exit_signal: result.signal || null,
      broker_restart_permitted: false,
      credential_values_read: false,
      cookies_or_tokens_read: false,
    },
  });
  throw new Error(`E_AUTH_HANDOFF_BROWSER_EXIT:${result.code ?? result.signal}`);
}
