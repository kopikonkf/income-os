import os from 'node:os';
import path from 'node:path';

export interface MuxiaPaths {
  root: string;
  profiles: string;
  jobs: string;
  artifacts: string;
  state: string;
  logs: string;
  locks: string;
  receipts: string;
}

export interface PathResolverOptions {
  root?: string;
  env?: NodeJS.ProcessEnv;
  homeDir?: string;
  pathApi?: Pick<typeof path, 'resolve' | 'join' | 'normalize' | 'relative' | 'isAbsolute'>;
}

export function resolveMuxiaPaths(options: PathResolverOptions = {}): MuxiaPaths {
  const env = options.env ?? process.env;
  const pathApi = options.pathApi ?? path;
  const configuredRoot = options.root ?? env.MUXIA_ROOT;
  const homeDir = options.homeDir ?? os.homedir();

  const root = pathApi.resolve(configuredRoot && configuredRoot.trim()
    ? configuredRoot.trim()
    : pathApi.join(homeDir, '.muxia'));

  return {
    root,
    profiles: pathApi.join(root, 'profiles'),
    jobs: pathApi.join(root, 'jobs'),
    artifacts: pathApi.join(root, 'artifacts'),
    state: pathApi.join(root, 'state'),
    logs: pathApi.join(root, 'logs'),
    locks: pathApi.join(root, 'state', 'locks'),
    receipts: pathApi.join(root, 'state', 'receipts'),
  };
}

export function isPathInside(
  root: string,
  candidate: string,
  pathApi: Pick<typeof path, 'resolve' | 'relative' | 'isAbsolute'> = path,
): boolean {
  const resolvedRoot = pathApi.resolve(root);
  const resolvedCandidate = pathApi.resolve(candidate);
  const relative = pathApi.relative(resolvedRoot, resolvedCandidate);
  return relative === '' || (!relative.startsWith('..') && !pathApi.isAbsolute(relative));
}

export function assertSafeId(value: string, label: string): void {
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(value)) {
    throw new Error(`INVALID_${label.toUpperCase()}_ID`);
  }
}
