#!/usr/bin/env node
import { runOperatorBrowser } from '../../../browser/linux/operator_browser_core.mjs';

const dieHome = process.env.DIE_HOME || '/srv/die';
const profileDir = process.env.DIE_DIVISION01_BROWSER_PROFILE || '/var/lib/die/division01/browser-profile';
const statusFile = process.env.DIE_DIVISION01_BROWSER_STATUS || '/var/lib/die/division01/browser-status.json';
const browserExecutable = process.env.DIE_DIVISION01_BROWSER_EXECUTABLE || process.env.DIE_BROWSER_EXECUTABLE || '/usr/bin/google-chrome-stable';
const command = process.argv[2] || 'probe';

try {
  const code = await runOperatorBrowser({
    dieHome,
    profileDir,
    statusFile,
    browserExecutable,
    browserClass: 'DIE-Division01-Stable',
    schema: 'die.division01.operator-browser.v1',
    principalId: 'division-head-division01',
    command,
  });
  process.exit(code);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(2);
}