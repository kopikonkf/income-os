#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { connectClusterBrowser } from '../../../browser/linux/cluster_broker_client.mjs';
import { probeProviderReadiness } from '../../../browser/linux/provider_readiness.mjs';

function arg(name, fallback = null) { const i = process.argv.indexOf(name); return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback; }
const dieHome = path.resolve(arg('--die-home', '/srv/die'));
const controlBaseUrl = String(arg('--control-base-url', '')).trim();
const providerId = String(arg('--provider-id', '')).trim();
const claimUrl = arg('--claim-url', null);
const profilesPath = path.resolve(arg('--profiles', path.join(dieHome, 'company/factory-asset/registries/provider-readiness-profiles.v1.json')));
const playwrightEntry = path.resolve(arg('--playwright-entry', path.join(dieHome, 'company/muxia/node_modules/playwright/index.mjs')));
if (!controlBaseUrl || !providerId) throw new Error('E_PROVIDER_READINESS_ARGS');
const profiles = JSON.parse(fs.readFileSync(profilesPath, 'utf8'));
const profile = profiles.providers?.[providerId];
if (!profile) throw new Error(`E_PROVIDER_READINESS_PROFILE:${providerId}`);
const { browser } = await connectClusterBrowser({ controlBaseUrl, playwrightEntry, timeoutMs: 10000 });
const context = browser.contexts()[0];
if (!context) throw new Error('E_PROVIDER_READINESS_CONTEXT');
const result = await probeProviderReadiness({ context, providerId, profile, claimUrl });
console.log(JSON.stringify(result));
process.exit(0);
