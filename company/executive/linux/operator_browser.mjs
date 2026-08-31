#!/usr/bin/env node
import { runOperatorBrowser } from '../../browser/linux/operator_browser_core.mjs';

const dieHome = process.env.DIE_HOME || '/srv/die';
const profileDir = process.env.DIE_EXECUTIVE_BROWSER_PROFILE || '/var/lib/die/executive/browser-profile';
const statusFile = process.env.DIE_EXECUTIVE_BROWSER_STATUS || '/var/lib/die/executive/browser-status.json';
const browserExecutable = process.env.DIE_EXECUTIVE_BROWSER_EXECUTABLE || process.env.DIE_BROWSER_EXECUTABLE || '/usr/bin/google-chrome-stable';
const command = process.argv[2] || 'probe';

try {
  const code = await runOperatorBrowser({
    dieHome,
    profileDir,
    statusFile,
    browserExecutable,
    browserClass: 'DIE-Executive-Stable',
    schema: 'die.executive.operator-browser.v1',
    principalId: 'die-lnx-executive-001',
    command,
  });
  process.exit(code);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(2);
}