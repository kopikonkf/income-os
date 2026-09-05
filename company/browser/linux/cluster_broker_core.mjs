import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';

function atomicWriteJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o750 });
  const tmp = `${file}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(value) + '\n', { mode: 0o640 });
  fs.renameSync(tmp, file);
}

function pidAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try { process.kill(pid, 0); return true; } catch { return false; }
}

function readLock(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; }
}

function acquireLock(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o750 });
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const fd = fs.openSync(file, 'wx', 0o640);
      fs.writeFileSync(fd, JSON.stringify(payload) + '\n');
      fs.closeSync(fd);
      return;
    } catch (error) {
      if (error?.code !== 'EEXIST') throw error;
      const current = readLock(file);
      if (current && pidAlive(Number(current.owner_pid))) throw new Error(`E_CLUSTER_BROKER_ALREADY_OWNED:${current.owner_pid}`);
      fs.rmSync(file, { force: true });
    }
  }
  throw new Error('E_CLUSTER_BROKER_LOCK_ACQUIRE');
}

function assertLoopbackHandle(handle) {
  if (!handle || handle.debugHost !== '127.0.0.1') throw new Error('E_CLUSTER_BROKER_NON_LOOPBACK_CDP');
  const parsed = new URL(handle.debugUrl);
  if (parsed.hostname !== '127.0.0.1') throw new Error('E_CLUSTER_BROKER_NON_LOOPBACK_CDP');
  if (Number(parsed.port) !== Number(handle.debugPort)) throw new Error('E_CLUSTER_BROKER_DEBUG_PORT_MISMATCH');
}

async function readJson(req, maxBytes = 16384) {
  const chunks = []; let bytes = 0;
  for await (const chunk of req) {
    bytes += chunk.length;
    if (bytes > maxBytes) throw new Error('E_CLUSTER_BROKER_REQUEST_TOO_LARGE');
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

function jsonReply(res, status, value) {
  res.statusCode = status;
  res.setHeader('content-type', 'application/json');
  res.end(JSON.stringify(value));
}

export class ClusterBrokerCore {
  constructor({ clusterId, profileId, profileDir, stateFile, lockFile, driver, maxTabs = 8, controlHost = '127.0.0.1', controlPort = 0, leaseManagerFactory = null }) {
    if (!clusterId || !profileId || !path.isAbsolute(profileDir) || !path.isAbsolute(stateFile) || !path.isAbsolute(lockFile)) throw new Error('E_CLUSTER_BROKER_CONFIG');
    if (controlHost !== '127.0.0.1') throw new Error('E_CLUSTER_BROKER_CONTROL_NOT_LOOPBACK');
    if (!Number.isInteger(maxTabs) || maxTabs < 1 || maxTabs > 8) throw new Error('E_CLUSTER_BROKER_TAB_CEILING');
    this.clusterId = clusterId; this.profileId = profileId; this.profileDir = profileDir;
    this.stateFile = stateFile; this.lockFile = lockFile; this.driver = driver; this.maxTabs = maxTabs;
    this.controlHost = controlHost; this.controlPort = controlPort; this.server = null; this.handle = null; this.state = null;
    this.leaseManagerFactory = leaseManagerFactory; this.leaseManager = null;
  }

  attachDescriptor() {
    if (!this.handle || !this.state || this.state.state !== 'READY') throw new Error('E_CLUSTER_BROKER_NOT_READY');
    return {
      schema: 'die.muxia.cluster-broker-attach.v1', cluster_id: this.clusterId, profile_id: this.profileId,
      debug_host: '127.0.0.1', debug_port: this.handle.debugPort, debug_url: this.handle.debugUrl,
      browser_owner_pid: this.handle.pid, max_tabs: this.maxTabs, broker_state: 'READY',
      credential_values_read: false, cookies_or_tokens_read: false,
    };
  }

  status() {
    const base = this.state ? { ...this.state } : { schema: 'die.muxia.cluster-broker-state.v1', cluster_id: this.clusterId, profile_id: this.profileId, state: 'OFFLINE' };
    if (this.leaseManager && base.state === 'READY') base.tab_leases = this.leaseManager.snapshot();
    return base;
  }

  async route(req, res) {
    try {
      if (req.method === 'GET' && req.url === '/v1/status') return jsonReply(res, 200, this.status());
      if (req.method === 'GET' && req.url === '/v1/attach') return jsonReply(res, 200, this.attachDescriptor());
      if (req.method === 'GET' && req.url === '/v1/leases') {
        if (!this.leaseManager) throw new Error('E_CLUSTER_TAB_LEASES_DISABLED');
        return jsonReply(res, 200, this.leaseManager.snapshot());
      }
      if (req.method === 'POST' && req.url === '/v1/leases/acquire') {
        if (!this.leaseManager) throw new Error('E_CLUSTER_TAB_LEASES_DISABLED');
        const body = await readJson(req);
        const lease = await this.leaseManager.acquire({ providerId: body.provider_id, jobId: body.job_id, ttlMs: body.ttl_ms ?? undefined });
        return jsonReply(res, 201, lease);
      }
      const release = req.url?.match(/^\/v1\/leases\/([^/]+)\/release$/);
      if (req.method === 'POST' && release) {
        if (!this.leaseManager) throw new Error('E_CLUSTER_TAB_LEASES_DISABLED');
        const body = await readJson(req);
        return jsonReply(res, 200, await this.leaseManager.release(decodeURIComponent(release[1]), body.reason || 'RELEASED'));
      }
      const mark = req.url?.match(/^\/v1\/leases\/([^/]+)\/state$/);
      if (req.method === 'POST' && mark) {
        if (!this.leaseManager) throw new Error('E_CLUSTER_TAB_LEASES_DISABLED');
        const body = await readJson(req);
        return jsonReply(res, 200, this.leaseManager.mark(decodeURIComponent(mark[1]), body.state));
      }
      const provider = req.url?.match(/^\/v1\/providers\/([^/]+)\/state$/);
      if (req.method === 'POST' && provider) {
        if (!this.leaseManager) throw new Error('E_CLUSTER_TAB_LEASES_DISABLED');
        const body = await readJson(req);
        return jsonReply(res, 200, this.leaseManager.setProviderState(decodeURIComponent(provider[1]), body.state));
      }
      if (req.method === 'POST' && req.url === '/v1/leases/reclaim') {
        if (!this.leaseManager) throw new Error('E_CLUSTER_TAB_LEASES_DISABLED');
        return jsonReply(res, 200, { reclaimed: await this.leaseManager.reclaimExpired(), snapshot: this.leaseManager.snapshot() });
      }
      return jsonReply(res, 404, { error: 'NOT_FOUND' });
    } catch (error) {
      const message = String(error?.message || error);
      const status = message.startsWith('E_PROVIDER_NOT_SCHEDULABLE') || message.startsWith('E_PROVIDER_TAB_CAPACITY') || message.startsWith('E_CLUSTER_TAB_CAPACITY') || message.startsWith('E_JOB_ALREADY_LEASED') ? 409 : 400;
      return jsonReply(res, status, { error: message });
    }
  }

  async start() {
    if (this.server || this.handle) throw new Error('E_CLUSTER_BROKER_ALREADY_STARTED');
    acquireLock(this.lockFile, { schema: 'die.muxia.cluster-broker-lock.v1', cluster_id: this.clusterId, profile_id: this.profileId, owner_pid: process.pid, acquired_at: new Date().toISOString() });
    try {
      this.handle = await this.driver.launch(this.profileDir);
      assertLoopbackHandle(this.handle);
      if (this.leaseManagerFactory) {
        const context = this.handle.browser.contexts()[0];
        if (!context) throw new Error('E_CLUSTER_BROKER_CONTEXT_MISSING');
        this.leaseManager = await this.leaseManagerFactory({ context, maxTabs: this.maxTabs });
      }
      this.server = http.createServer((req, res) => { void this.route(req, res); });
      await new Promise((resolve, reject) => { this.server.once('error', reject); this.server.listen(this.controlPort, this.controlHost, resolve); });
      const addr = this.server.address();
      if (!addr || typeof addr === 'string' || addr.address !== '127.0.0.1') throw new Error('E_CLUSTER_BROKER_CONTROL_BIND');
      this.state = {
        schema: 'die.muxia.cluster-broker-state.v1', cluster_id: this.clusterId, profile_id: this.profileId,
        profile_dir: this.profileDir, state: 'READY', browser_owner_pid: this.handle.pid,
        browser_owner_model: 'SINGLE_LONG_LIVED_CHROMIUM_PROCESS', debug_host: '127.0.0.1', debug_port: this.handle.debugPort,
        control_host: '127.0.0.1', control_port: addr.port, max_tabs: this.maxTabs, started_at: new Date().toISOString(),
        credential_values_read: false, cookies_or_tokens_read: false,
      };
      atomicWriteJson(this.stateFile, this.state);
      return this.status();
    } catch (error) {
      await this.stop().catch(() => {});
      throw error;
    }
  }

  async stop() {
    const server = this.server; this.server = null;
    if (server) await new Promise((resolve) => server.close(() => resolve()));
    if (this.leaseManager) { await this.leaseManager.releaseAll('BROKER_STOP'); this.leaseManager = null; }
    if (this.handle) { await this.driver.stop(); this.handle = null; }
    this.state = {
      schema: 'die.muxia.cluster-broker-state.v1', cluster_id: this.clusterId, profile_id: this.profileId,
      state: 'OFFLINE', stopped_at: new Date().toISOString(), credential_values_read: false, cookies_or_tokens_read: false,
    };
    atomicWriteJson(this.stateFile, this.state);
    fs.rmSync(this.lockFile, { force: true });
  }
}
