import path from 'node:path';
import { pathToFileURL } from 'node:url';

function assertLoopback(controlBaseUrl) {
  const u = new URL(controlBaseUrl);
  if (u.hostname !== '127.0.0.1') throw new Error('E_CLUSTER_BROKER_CLIENT_NOT_LOOPBACK');
  return u;
}

async function requestJson(controlBaseUrl, pathname, { method = 'GET', body = null, timeoutMs = 5000 } = {}) {
  const base = assertLoopback(controlBaseUrl);
  const u = new URL(pathname, base);
  const init = { method, signal: AbortSignal.timeout(timeoutMs), headers: {} };
  if (body !== null) { init.headers['content-type'] = 'application/json'; init.body = JSON.stringify(body); }
  const r = await fetch(u, init);
  const v = await r.json().catch(() => ({ error: `HTTP_${r.status}` }));
  if (!r.ok) throw new Error(v.error || `E_CLUSTER_BROKER_HTTP_${r.status}`);
  return v;
}

export async function fetchClusterAttach(controlBaseUrl, timeoutMs = 5000) {
  const v = await requestJson(controlBaseUrl, '/v1/attach', { timeoutMs });
  if (v.schema !== 'die.muxia.cluster-broker-attach.v1' || v.debug_host !== '127.0.0.1') throw new Error('E_CLUSTER_BROKER_ATTACH_SCHEMA');
  return v;
}

export async function acquireClusterTab(controlBaseUrl, { providerId, jobId, ttlMs = undefined, timeoutMs = 5000 }) {
  return await requestJson(controlBaseUrl, '/v1/leases/acquire', { method: 'POST', body: { provider_id: providerId, job_id: jobId, ttl_ms: ttlMs }, timeoutMs });
}

export async function releaseClusterTab(controlBaseUrl, leaseId, reason = 'RELEASED', timeoutMs = 5000) {
  return await requestJson(controlBaseUrl, `/v1/leases/${encodeURIComponent(leaseId)}/release`, { method: 'POST', body: { reason }, timeoutMs });
}

export async function markClusterTab(controlBaseUrl, leaseId, state, timeoutMs = 5000) {
  return await requestJson(controlBaseUrl, `/v1/leases/${encodeURIComponent(leaseId)}/state`, { method: 'POST', body: { state }, timeoutMs });
}

export async function setClusterProviderState(controlBaseUrl, providerId, state, timeoutMs = 5000) {
  return await requestJson(controlBaseUrl, `/v1/providers/${encodeURIComponent(providerId)}/state`, { method: 'POST', body: { state }, timeoutMs });
}

export async function fetchClusterLeases(controlBaseUrl, timeoutMs = 5000) {
  return await requestJson(controlBaseUrl, '/v1/leases', { timeoutMs });
}

export async function connectClusterBrowser({ controlBaseUrl, playwrightEntry, timeoutMs = 10000 }) {
  const attach = await fetchClusterAttach(controlBaseUrl, timeoutMs);
  const { chromium } = await import(pathToFileURL(path.resolve(playwrightEntry)).href);
  const browser = await chromium.connectOverCDP(attach.debug_url, { timeout: timeoutMs });
  return { browser, attach, ownership: 'BROKER_OWNS_BROWSER' };
}

export async function connectLeasedClusterTab({ controlBaseUrl, lease, playwrightEntry, timeoutMs = 10000 }) {
  const { browser, attach } = await connectClusterBrowser({ controlBaseUrl, playwrightEntry, timeoutMs });
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (const context of browser.contexts()) {
      const page = context.pages().find((p) => p.url() === lease.claim_url);
      if (page) return { browser, page, attach, lease, ownership: 'BROKER_OWNS_BROWSER' };
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error(`E_CLUSTER_TAB_CLAIM_TIMEOUT:${lease.lease_id}`);
}