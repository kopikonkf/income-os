import path from 'node:path';
import { pathToFileURL } from 'node:url';

export async function fetchClusterAttach(controlBaseUrl, timeoutMs = 5000) {
  const u = new URL('/v1/attach', controlBaseUrl);
  if (u.hostname !== '127.0.0.1') throw new Error('E_CLUSTER_BROKER_CLIENT_NOT_LOOPBACK');
  const r = await fetch(u, { signal: AbortSignal.timeout(timeoutMs) });
  if (!r.ok) throw new Error(`E_CLUSTER_BROKER_ATTACH_HTTP_${r.status}`);
  const v = await r.json();
  if (v.schema !== 'die.muxia.cluster-broker-attach.v1' || v.debug_host !== '127.0.0.1') throw new Error('E_CLUSTER_BROKER_ATTACH_SCHEMA');
  return v;
}

export async function connectClusterBrowser({ controlBaseUrl, playwrightEntry, timeoutMs = 10000 }) {
  const attach = await fetchClusterAttach(controlBaseUrl, timeoutMs);
  const { chromium } = await import(pathToFileURL(path.resolve(playwrightEntry)).href);
  const browser = await chromium.connectOverCDP(attach.debug_url, { timeout: timeoutMs });
  return { browser, attach };
}
