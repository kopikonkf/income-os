#!/usr/bin/env node
import path from 'node:path';
import { runWakeTransport } from '../../../browser/linux/wake_transport_core.mjs';
const dieHome = process.env.DIE_WAKE_SOURCE_ROOT || process.env.DIE_HOME || '/srv/die';
const command = process.argv[2] || 'focus';
const envelopeFile = process.argv[3] ? path.resolve(process.argv[3]) : null;
try {
  const out = await runWakeTransport({ dieHome, principalId: 'die-lnx-division-001', statusFile: process.env.DIE_DIVISION01_BROWSER_STATUS || '/var/lib/die/division01/browser-status.json', threadStateFile: process.env.DIE_DIVISION01_WAKE_THREAD || '/var/lib/die/division01/wake-thread.json', receiptDir: process.env.DIE_DIVISION01_WAKE_RECEIPTS || '/var/lib/die/division01/wake-receipts', command, envelopeFile });
  console.log(JSON.stringify(out));
} catch (error) { console.error(error instanceof Error ? error.message : String(error)); process.exit(2); }
