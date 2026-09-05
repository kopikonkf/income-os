import crypto from 'node:crypto';

const BLOCKING_PROVIDER_STATES = new Set(['AUTH_REQUIRED', 'CHECKPOINT', 'UNAVAILABLE']);
const ALLOWED_PROVIDER_STATES = new Set(['HEALTHY', 'DEGRADED', 'AUTH_REQUIRED', 'CHECKPOINT', 'UNAVAILABLE']);
const ALLOWED_LEASE_STATES = new Set(['LEASED', 'IN_FLIGHT', 'COOLDOWN', 'CHECKPOINT', 'FAILED']);

function validId(value) { return typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:-]{1,160}$/.test(value); }

export class ClusterTabLeaseManager {
  constructor({ context, maxTabs = 8, providerLimits = {}, defaultProviderLimit = 1, defaultTtlMs = 300000, now = () => Date.now() }) {
    if (!context || typeof context.pages !== 'function' || typeof context.newPage !== 'function') throw new Error('E_TAB_LEASE_CONTEXT');
    if (!Number.isInteger(maxTabs) || maxTabs < 1 || maxTabs > 8) throw new Error('E_TAB_LEASE_MAX_TABS');
    if (!Number.isInteger(defaultProviderLimit) || defaultProviderLimit < 1 || defaultProviderLimit > maxTabs) throw new Error('E_TAB_LEASE_PROVIDER_LIMIT');
    this.context = context; this.maxTabs = maxTabs; this.providerLimits = { ...providerLimits };
    this.defaultProviderLimit = defaultProviderLimit; this.defaultTtlMs = defaultTtlMs; this.now = now;
    this.leases = new Map(); this.providerStates = new Map();
  }

  providerState(providerId) { return this.providerStates.get(providerId) || 'HEALTHY'; }
  setProviderState(providerId, state) {
    if (!validId(providerId) || !ALLOWED_PROVIDER_STATES.has(state)) throw new Error('E_PROVIDER_STATE');
    this.providerStates.set(providerId, state);
    return { provider_id: providerId, state };
  }
  providerLimit(providerId) {
    const value = this.providerLimits[providerId] ?? this.defaultProviderLimit;
    if (!Number.isInteger(value) || value < 1 || value > this.maxTabs) throw new Error(`E_PROVIDER_LIMIT_CONFIG:${providerId}`);
    return value;
  }
  publicLease(lease) {
    return {
      schema: 'die.muxia.cluster-tab-lease.v1', lease_id: lease.leaseId, provider_id: lease.providerId,
      job_id: lease.jobId, state: lease.state, claim_url: lease.claimUrl,
      acquired_at: new Date(lease.acquiredAt).toISOString(), expires_at: new Date(lease.expiresAt).toISOString(),
      max_tabs: this.maxTabs, provider_limit: this.providerLimit(lease.providerId),
    };
  }
  activeForProvider(providerId) { return [...this.leases.values()].filter((x) => x.providerId === providerId).length; }
  pageIsLeased(page) { return [...this.leases.values()].some((x) => x.page === page); }

  async acquire({ providerId, jobId, ttlMs = this.defaultTtlMs }) {
    if (!validId(providerId) || !validId(jobId)) throw new Error('E_TAB_LEASE_ID');
    if (!Number.isInteger(ttlMs) || ttlMs < 1000 || ttlMs > 3600000) throw new Error('E_TAB_LEASE_TTL');
    await this.reclaimExpired();
    if (BLOCKING_PROVIDER_STATES.has(this.providerState(providerId))) throw new Error(`E_PROVIDER_NOT_SCHEDULABLE:${providerId}:${this.providerState(providerId)}`);
    if ([...this.leases.values()].some((x) => x.jobId === jobId)) throw new Error(`E_JOB_ALREADY_LEASED:${jobId}`);
    if (this.activeForProvider(providerId) >= this.providerLimit(providerId)) throw new Error(`E_PROVIDER_TAB_CAPACITY:${providerId}`);
    if (this.leases.size >= this.maxTabs) throw new Error('E_CLUSTER_TAB_CAPACITY');

    const openPages = this.context.pages().filter((page) => !page.isClosed());
    let page = openPages.find((x) => x.url() === 'about:blank' && !this.pageIsLeased(x));
    if (!page) {
      if (openPages.length >= this.maxTabs) throw new Error('E_CLUSTER_TAB_CAPACITY_UNMANAGED_PAGES');
      page = await this.context.newPage();
    }
    const leaseId = crypto.randomUUID();
    const claimUrl = `about:blank#die-lease=${leaseId}`;
    await page.goto(claimUrl);
    const acquiredAt = this.now();
    const lease = { leaseId, providerId, jobId, state: 'LEASED', claimUrl, acquiredAt, expiresAt: acquiredAt + ttlMs, page };
    this.leases.set(leaseId, lease);
    return this.publicLease(lease);
  }

  mark(leaseId, state) {
    const lease = this.leases.get(leaseId); if (!lease) throw new Error(`E_TAB_LEASE_NOT_FOUND:${leaseId}`);
    if (!ALLOWED_LEASE_STATES.has(state)) throw new Error('E_TAB_LEASE_STATE');
    lease.state = state; return this.publicLease(lease);
  }

  async release(leaseId, reason = 'RELEASED') {
    const lease = this.leases.get(leaseId); if (!lease) return { lease_id: leaseId, released: false, reason: 'NOT_FOUND' };
    this.leases.delete(leaseId);
    await lease.page.close({ runBeforeUnload: false }).catch(() => {});
    return { lease_id: leaseId, released: true, reason, provider_id: lease.providerId, job_id: lease.jobId };
  }

  async reclaimExpired() {
    const now = this.now(); const reclaimed = [];
    for (const [id, lease] of [...this.leases.entries()]) if (lease.expiresAt <= now || lease.page.isClosed()) reclaimed.push(await this.release(id, lease.page.isClosed() ? 'PAGE_CLOSED' : 'TTL_EXPIRED'));
    return reclaimed;
  }

  async releaseAll(reason = 'BROKER_STOP') {
    const out = []; for (const id of [...this.leases.keys()]) out.push(await this.release(id, reason)); return out;
  }

  snapshot() {
    const providerStates = {};
    for (const [k, v] of this.providerStates.entries()) providerStates[k] = v;
    return {
      schema: 'die.muxia.cluster-tab-lease-snapshot.v1', max_tabs: this.maxTabs, active_leases: this.leases.size,
      open_pages: this.context.pages().filter((p) => !p.isClosed()).length,
      provider_states: providerStates,
      leases: [...this.leases.values()].map((x) => this.publicLease(x)),
    };
  }
}
