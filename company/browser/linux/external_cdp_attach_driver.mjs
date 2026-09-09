import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

function pidAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try { process.kill(pid, 0); return true; } catch { return false; }
}

export class ExternalCdpAttachDriver {
  constructor({ debugHost = '127.0.0.1', debugPort, playwrightEntry, ownerPidFile, connectTimeoutMs = 30000 }) {
    if (debugHost !== '127.0.0.1') throw new Error('E_EXTERNAL_CDP_NON_LOOPBACK');
    if (!Number.isInteger(debugPort) || debugPort < 1024 || debugPort > 65535) throw new Error('E_EXTERNAL_CDP_PORT');
    if (!playwrightEntry || !ownerPidFile) throw new Error('E_EXTERNAL_CDP_CONFIG');
    this.debugHost = debugHost; this.debugPort = debugPort; this.debugUrl = `http://${debugHost}:${debugPort}`;
    this.playwrightEntry = playwrightEntry; this.ownerPidFile = ownerPidFile; this.connectTimeoutMs = connectTimeoutMs; this.browser = null;
  }

  ownerPid() {
    const pid = Number(String(fs.readFileSync(this.ownerPidFile, 'utf8')).trim());
    if (!pidAlive(pid)) throw new Error('E_EXTERNAL_CDP_OWNER_NOT_ALIVE');
    return pid;
  }

  async launch(profileDir) {
    const pid = this.ownerPid();
    const response = await fetch(`${this.debugUrl}/json/version`, { signal: AbortSignal.timeout(this.connectTimeoutMs) });
    if (!response.ok) throw new Error(`E_EXTERNAL_CDP_VERSION_HTTP_${response.status}`);
    const version = await response.json();
    if (!String(version?.webSocketDebuggerUrl || '').startsWith(`ws://${this.debugHost}:${this.debugPort}/`)) throw new Error('E_EXTERNAL_CDP_ENDPOINT_MISMATCH');
    const pw = await import(pathToFileURL(this.playwrightEntry).href);
    this.browser = await pw.chromium.connectOverCDP(this.debugUrl, { timeout: this.connectTimeoutMs });
    if (!this.browser.isConnected()) throw new Error('E_EXTERNAL_CDP_NOT_CONNECTED');
    if (!this.browser.contexts().length) throw new Error('E_EXTERNAL_CDP_CONTEXT_MISSING');
    return {
      pid, userDataDir: profileDir, debugHost: this.debugHost, debugPort: this.debugPort, debugUrl: this.debugUrl,
      browser: this.browser, ownerModel: 'EXTERNAL_PERSISTENT_CHROME_CDP_ATTACH_ONLY', externalOwner: true,
    };
  }

  async stop() {
    // Deliberately do not Browser.close(): the browser lifecycle belongs to the
    // external owner service. Broker process exit drops the CDP websocket only.
    this.browser = null;
  }
}
