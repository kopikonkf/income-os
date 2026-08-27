import { spawnSync } from 'node:child_process';
import { resolveMuxiaPaths } from '../dist/core/paths.js';
import { ProfileRegistry } from '../dist/core/profile-registry.js';

const root = process.env.MUXIA_ROOT ?? 'C:\\DIE\\workspaces\\MUXIA-B04\\muxia-root';
const paths = resolveMuxiaPaths({ root });
const profiles = new ProfileRegistry(paths);
const ids = ['chatgpt-b','chatgpt-c','chatgpt-d','chatgpt-e'];
const results = [];

for (const id of ids) {
  const before = profiles.get(id);
  const owner = `mx-043-${id}`;
  if (before.browserPid) {
    spawnSync('taskkill.exe', ['/PID', String(before.browserPid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
  }
  let released = false;
  let releaseError = null;
  try {
    const current = profiles.get(id);
    if (current.leaseOwner === owner) {
      profiles.releaseLease(id, owner);
      released = true;
    }
  } catch (error) {
    releaseError = error instanceof Error ? error.message : String(error);
  }
  const after = profiles.get(id);
  results.push({ id, before, released, releaseError, after });
}

const pass = results.every((r) => r.after.state === 'READY' && r.after.leaseOwner === null && r.after.browserPid === null && r.releaseError === null);
console.log(JSON.stringify({ schema:'die.muxia.mx043-r1.teardown.v1', task_id:'MX-043-R1', pass, results }, null, 2));
if (!pass) process.exit(2);
