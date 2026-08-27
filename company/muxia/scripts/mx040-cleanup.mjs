import { resolveMuxiaPaths } from '../dist/core/paths.js';
import { ProfileRegistry } from '../dist/core/profile-registry.js';

const root = process.env.MUXIA_ROOT ?? 'C:\\DIE\\workspaces\\MUXIA-B04\\muxia-root';
const paths = resolveMuxiaPaths({ root });
const registry = new ProfileRegistry(paths);
for (const [profileId, owner] of [['chatgpt-b','mx040-owner-b'], ['chatgpt-a','mx040-owner-a']]) {
  try {
    const before = registry.get(profileId);
    if (before.leaseOwner === owner) {
      const after = registry.releaseLease(profileId, owner);
      console.log(JSON.stringify({ profileId, released: true, state: after.state, leaseOwner: after.leaseOwner }));
    } else {
      console.log(JSON.stringify({ profileId, released: false, reason: 'OWNER_NOT_MATCHING', state: before.state, leaseOwner: before.leaseOwner }));
    }
  } catch (error) {
    console.log(JSON.stringify({ profileId, released: false, error: String(error?.message ?? error) }));
  }
}
