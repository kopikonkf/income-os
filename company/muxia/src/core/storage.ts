import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import type { MuxiaPaths } from './paths.js';

export function ensureMuxiaLayout(paths: MuxiaPaths): void {
  for (const dir of [paths.root, paths.profiles, paths.jobs, paths.artifacts, paths.state, paths.logs, paths.locks, paths.receipts]) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

export function readJsonFile<T>(filePath: string): T {
  return JSON.parse(fs.readFileSync(filePath, 'utf8')) as T;
}

export function writeJsonAtomic(filePath: string, value: unknown): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tmp = `${filePath}.${process.pid}.${crypto.randomUUID()}.tmp`;
  const payload = `${JSON.stringify(value, null, 2)}\n`;
  const fd = fs.openSync(tmp, 'wx', 0o600);
  try {
    fs.writeFileSync(fd, payload, { encoding: 'utf8' });
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  fs.renameSync(tmp, filePath);
}

export function listJsonFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
    .map((entry) => path.join(dir, entry.name))
    .sort();
}

export function assertNoSecretLikeKeys(value: unknown, trail = 'root'): void {
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertNoSecretLikeKeys(item, `${trail}[${index}]`));
    return;
  }
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    if (/(cookie|token|password|secret|credential|authorization|localstorage|sessionstorage)/i.test(key)) {
      throw new Error(`SECRET_LIKE_FIELD_REJECTED:${trail}.${key}`);
    }
    assertNoSecretLikeKeys(child, `${trail}.${key}`);
  }
}
