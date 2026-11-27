import crypto from 'node:crypto';

const BLOCKING_PROVIDER_STATES = new Set(['AUTH_REQUIRED', 'CHECKPOINT', 'UNAVAILABLE']);
const ALLOWED_PROVIDER_STATES = new Set(['HEALTHY', 'DEGRADED', 'AUTH_REQUIRED', 'CHECKPOINT', 'UNAVAILABLE']);
const ALLOWED_LEASE_STATES = new Set(['LEASED', 'IN_FLIGHT', 'COOLDOWN', 'CHECKPOINT', 'FAILED']);
const ALLOWED_LEASE_PURPOSES = new Set(['GENERATION', 'READINESS_PROBE']);

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
      job_id: lease.jobId, state: lease.state, purpose: lease.purpose, claim_url: lease.claimUrl, target_id: lease.targetId || null,
      acquired_at: new Date(lease.acquiredAt).toISOString(), expires_at: new Date(lease.expiresAt).toISOString(),
      max_tabs: this.maxTabs, provider_limit: this.providerLimit(lease.providerId),
    };
  }
  activeForProvider(providerId) { return [...this.leases.values()].filter((x) => x.providerId === providerId).length; }
  pageIsLeased(page) { return [...this.leases.values()].some((x) => x.page === page); }

  async acquire({ providerId, jobId, ttlMs = this.defaultTtlMs, purpose = 'GENERATION' }) {
    if (!validId(providerId) || !validId(jobId)) throw new Error('E_TAB_LEASE_ID');
    if (!Number.isInteger(ttlMs) || ttlMs < 1000 || ttlMs > 3600000) throw new Error('E_TAB_LEASE_TTL');
    if (!ALLOWED_LEASE_PURPOSES.has(purpose)) throw new Error('E_TAB_LEASE_PURPOSE');
    await this.reclaimExpired();
    if (BLOCKING_PROVIDER_STATES.has(this.providerState(providerId)) && purpose !== 'READINESS_PROBE') throw new Error(`E_PROVIDER_NOT_SCHEDULABLE:${providerId}:${this.providerState(providerId)}`);
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
    let targetId = null;
    if (typeof this.context.newCDPSession === 'function') {
      let session = null;
      try { session = await this.context.newCDPSession(page); const info = await session.send('Target.getTargetInfo'); targetId = info?.targetInfo?.targetId || null; }
      catch {} finally { if (session?.detach) await session.detach().catch(() => {}); }
    }
    const acquiredAt = this.now();
    const lease = { leaseId, providerId, jobId, purpose, state: 'LEASED', claimUrl, targetId, acquiredAt, expiresAt: acquiredAt + ttlMs, page };
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
    let pageRecycled = false; let standbyCreated = false;
    if (!lease.page.isClosed()) {
      try {
        await lease.page.goto('about:blank');
        pageRecycled = !lease.page.isClosed() && lease.page.url() === 'about:blank';
      } catch {}
    }
    if (!pageRecycled) {
      const otherOpen = this.context.pages().filter((page) => page !== lease.page && !page.isClosed());
      if (!otherOpen.length) { try { await this.context.newPage(); standbyCreated = true; } catch {} }
      if (!lease.page.isClosed()) await lease.page.close({ runBeforeUnload: false }).catch(() => {});
    }
    let idlePagesCompacted = 0;
    if (this.leases.size === 0) {
      const idle = this.context.pages().filter((page) => !page.isClosed() && page.url() === 'about:blank');
      for (const extra of idle.slice(1)) {
        await extra.close({ runBeforeUnload: false }).catch(() => {});
        if (extra.isClosed()) idlePagesCompacted += 1;
      }
    }
    return { lease_id: leaseId, released: true, reason, provider_id: lease.providerId, job_id: lease.jobId, page_recycled: pageRecycled, standby_created: standbyCreated, idle_pages_compacted: idlePagesCompacted };
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
