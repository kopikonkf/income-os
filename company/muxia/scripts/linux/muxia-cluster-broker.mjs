#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { ClusterBrokerCore } from '../../../browser/linux/cluster_broker_core.mjs';
import { ClusterTabLeaseManager } from '../../../browser/linux/cluster_tab_leases.mjs';

function arg(name, fallback = null) { const i = process.argv.indexOf(name); return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback; }
const dieHome = path.resolve(arg('--die-home', '/srv/die'));
const clusterId = String(arg('--cluster-id', 'cluster-a'));
const registryPath = path.resolve(arg('--registry', path.join(dieHome, 'company/factory-asset/registries/web-ai-clusters.v1.json')));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const cluster = registry.clusters.find((x) => x.cluster_id === clusterId);
if (!cluster) throw new Error(`E_CLUSTER_NOT_REGISTERED:${clusterId}`);
const stateRoot = path.resolve(arg('--state-root', '/var/lib/muxia/state/cluster-brokers'));
const browserExecutable = path.resolve(arg('--browser-executable', '/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome'));
const headless = String(arg('--headless', 'true')).toLowerCase() !== 'false';
const { PlaywrightChromiumDriver } = await import(pathToFileURL(path.join(dieHome, 'company/muxia/dist/browser/playwright-driver.js')).href);
const driver = new PlaywrightChromiumDriver({ executablePath: browserExecutable, headless, launchTimeoutMs: 30000, shutdownTimeoutMs: 8000 });
const providerLimits = cluster.provider_tab_limits || Object.fromEntries((cluster.providers || []).filter((x) => x.membership === 'ACTIVE').map((x) => [x.provider_id, 1]));
const defaultTtlMs = Number(cluster.lease_default_ttl_seconds || 300) * 1000;
const broker = new ClusterBrokerCore({
  clusterId: cluster.cluster_id,
  profileId: cluster.profile_id,
  profileDir: cluster.profile_dir,
  stateFile: path.join(stateRoot, `${cluster.cluster_id}.json`),
  lockFile: path.join(stateRoot, `${cluster.cluster_id}.lock`),
  driver,
  maxTabs: cluster.max_tabs,
  controlHost: '127.0.0.1',
  controlPort: Number(arg('--control-port', '0')),
  leaseManagerFactory: ({ context, maxTabs }) => new ClusterTabLeaseManager({ context, maxTabs, providerLimits, defaultProviderLimit: 1, defaultTtlMs }),
});
const state = await broker.start();
console.log(JSON.stringify(state));
await new Promise((resolve) => { process.once('SIGINT', resolve); process.once('SIGTERM', resolve); });
await broker.stop();