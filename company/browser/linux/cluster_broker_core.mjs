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
      if (current && pidAlive(Number(current.owner_pid))) {
        throw new Error(`E_CLUSTER_BROKER_ALREADY_OWNED:${current.owner_pid}`);
      }
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

export class ClusterBrokerCore {
  constructor({ clusterId, profileId, profileDir, stateFile, lockFile, driver, maxTabs = 8, controlHost = '127.0.0.1', controlPort = 0 }) {
    if (!clusterId || !profileId || !path.isAbsolute(profileDir) || !path.isAbsolute(stateFile) || !path.isAbsolute(lockFile)) throw new Error('E_CLUSTER_BROKER_CONFIG');
    if (controlHost !== '127.0.0.1') throw new Error('E_CLUSTER_BROKER_CONTROL_NOT_LOOPBACK');
    if (!Number.isInteger(maxTabs) || maxTabs < 1 || maxTabs > 8) throw new Error('E_CLUSTER_BROKER_TAB_CEILING');
    this.clusterId = clusterId; this.profileId = profileId; this.profileDir = profileDir;
    this.stateFile = stateFile; this.lockFile = lockFile; this.driver = driver; this.maxTabs = maxTabs;
    this.controlHost = controlHost; this.controlPort = controlPort; this.server = null; this.handle = null; this.state = null;
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

  status() { return this.state ? { ...this.state } : { schema: 'die.muxia.cluster-broker-state.v1', cluster_id: this.clusterId, profile_id: this.profileId, state: 'OFFLINE' }; }

  async start() {
    if (this.server || this.handle) throw new Error('E_CLUSTER_BROKER_ALREADY_STARTED');
    acquireLock(this.lockFile, { schema: 'die.muxia.cluster-broker-lock.v1', cluster_id: this.clusterId, profile_id: this.profileId, owner_pid: process.pid, acquired_at: new Date().toISOString() });
    try {
      this.handle = await this.driver.launch(this.profileDir);
      assertLoopbackHandle(this.handle);
      this.server = http.createServer((req, res) => {
        res.setHeader('content-type', 'application/json');
        if (req.method === 'GET' && req.url === '/v1/status') { res.end(JSON.stringify(this.status())); return; }
        if (req.method === 'GET' && req.url === '/v1/attach') { try { res.end(JSON.stringify(this.attachDescriptor())); } catch (e) { res.statusCode = 503; res.end(JSON.stringify({ error: String(e?.message || e) })); } return; }
        res.statusCode = 404; res.end(JSON.stringify({ error: 'NOT_FOUND' }));
      });
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
    if (this.handle) { await this.driver.stop(); this.handle = null; }
    this.state = {
      schema: 'die.muxia.cluster-broker-state.v1', cluster_id: this.clusterId, profile_id: this.profileId,
      state: 'OFFLINE', stopped_at: new Date().toISOString(), credential_values_read: false, cookies_or_tokens_read: false,
    };
    atomicWriteJson(this.stateFile, this.state);
    fs.rmSync(this.lockFile, { force: true });
  }
}
