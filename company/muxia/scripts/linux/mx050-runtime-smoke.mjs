import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { chromium } from 'playwright';

if (process.platform !== 'linux') {
  throw new Error(`MX050_REQUIRES_LINUX:${process.platform}`);
}

const root = process.env.MUXIA_ROOT?.trim() || path.join(os.homedir(), '.muxia');
const profileDir = path.join(root, 'profiles', 'mx050-linux-smoke', 'browser');
fs.mkdirSync(profileDir, { recursive: true });

const startedAt = new Date().toISOString();
const context = await chromium.launchPersistentContext(profileDir, {
  headless: true,
  args: ['--remote-debugging-address=127.0.0.1'],
});
try {
  const page = context.pages()[0] ?? await context.newPage();
  await page.goto('data:text/html,<title>MUXIA MX-050</title><body>linux-smoke</body>', { waitUntil: 'load' });
  const title = await page.title();
  if (title !== 'MUXIA MX-050') throw new Error(`MX050_SMOKE_TITLE_MISMATCH:${title}`);
  const result = {
    schema: 'die.muxia.mx050.linux-runtime-smoke.v1',
    task_id: 'MX-050',
    platform: process.platform,
    arch: process.arch,
    node: process.version,
    playwright_chromium_executable: chromium.executablePath(),
    muxia_root: root,
    profile_dir: profileDir,
    headless: true,
    electron_dependency_used: false,
    title,
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    status: 'PASS'
  };
  const stateDir = path.join(root, 'state');
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, 'mx050-linux-runtime-smoke.json'), `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(result, null, 2));
} finally {
  await context.close();
}
