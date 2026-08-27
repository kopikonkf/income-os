import fs from 'node:fs';
import path from 'node:path';
import { execFileSync, spawn, type ChildProcess } from 'node:child_process';
import { chromium, type Browser } from 'playwright';
import { isPathInside } from '../core/paths.js';

export interface PlaywrightDriverOptions {
  executablePath?: string;
  headless?: boolean;
  launchTimeoutMs?: number;
  shutdownTimeoutMs?: number;
}

export interface BrowserRuntimeHandle {
  pid: number;
  userDataDir: string;
  debugHost: '127.0.0.1';
  debugPort: number;
  debugUrl: string;
  browser: Browser;
}

interface InternalHandle extends BrowserRuntimeHandle {
  process: ChildProcess;
}

const DEVTOOLS_ACTIVE_PORT = 'DevToolsActivePort';
const TRANSIENT_DEVTOOLS_READ_ERRORS = new Set(['ENOENT', 'EBUSY', 'EACCES']);

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function settleWithin<T>(promise: Promise<T>, timeoutMs: number): Promise<boolean> {
  return await Promise.race([
    promise.then(() => true, () => true),
    delay(timeoutMs).then(() => false),
  ]);
}

function assertDedicatedProfileRoot(userDataDir: string): void {
  const resolved = path.resolve(userDataDir);
  if (resolved === path.parse(resolved).root) throw new Error('BROWSER_PROFILE_ROOT_TOO_BROAD');
  if (resolved.length < path.parse(resolved).root.length + 4) throw new Error('BROWSER_PROFILE_ROOT_TOO_BROAD');
}

async function waitForDevToolsPort(userDataDir: string, process: ChildProcess, timeoutMs: number): Promise<number> {
  const activePortFile = path.join(userDataDir, DEVTOOLS_ACTIVE_PORT);
  const deadline = Date.now() + timeoutMs;
  let stderr = '';

  process.stderr?.on('data', (chunk: Buffer | string) => {
    stderr = `${stderr}${chunk.toString()}`.slice(-8192);
  });

  while (Date.now() < deadline) {
    if (process.exitCode !== null) {
      throw new Error(`CHROMIUM_EXITED_BEFORE_READY:${process.exitCode}:${stderr}`);
    }
    try {
      const lines = fs.readFileSync(activePortFile, 'utf8').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
      const port = Number(lines[0]);
      if (Number.isInteger(port) && port > 0 && port <= 65535) return port;
    } catch (error) {
      const code = (error as NodeJS.ErrnoException).code;
      if (!code || !TRANSIENT_DEVTOOLS_READ_ERRORS.has(code)) throw error;
    }
    await delay(50);
  }
  throw new Error(`CHROMIUM_DEBUG_PORT_TIMEOUT:${timeoutMs}`);
}

async function waitForExit(process: ChildProcess, timeoutMs: number): Promise<boolean> {
  if (process.exitCode !== null) return true;
  return await new Promise<boolean>((resolve) => {
    const timer = setTimeout(() => {
      cleanup();
      resolve(false);
    }, timeoutMs);
    const onExit = () => {
      cleanup();
      resolve(true);
    };
    const cleanup = () => {
      clearTimeout(timer);
      process.off('exit', onExit);
    };
    process.once('exit', onExit);
  });
}

function terminateProcessTree(pid: number): void {
  if (process.platform === 'win32') {
    try {
      execFileSync('taskkill.exe', ['/PID', String(pid), '/T', '/F'], {
        stdio: 'ignore',
        windowsHide: true,
      });
    } catch {
      // The process may already be gone.
    }
    return;
  }
  try {
    process.kill(pid, 'SIGTERM');
  } catch {
    // The process may already be gone.
  }
}

export class PlaywrightChromiumDriver {
  private readonly executablePath: string;
  private readonly headless: boolean;
  private readonly launchTimeoutMs: number;
  private readonly shutdownTimeoutMs: number;
  private active: InternalHandle | null = null;

  constructor(options: PlaywrightDriverOptions = {}) {
    this.executablePath = options.executablePath ?? chromium.executablePath();
    this.headless = options.headless ?? true;
    this.launchTimeoutMs = options.launchTimeoutMs ?? 20_000;
    this.shutdownTimeoutMs = options.shutdownTimeoutMs ?? 5_000;
  }

  get activeHandle(): BrowserRuntimeHandle | null {
    return this.active;
  }

  async launch(userDataDir: string): Promise<BrowserRuntimeHandle> {
    if (this.active !== null) throw new Error('BROWSER_ALREADY_RUNNING');
    const resolvedProfile = path.resolve(userDataDir);
    assertDedicatedProfileRoot(resolvedProfile);
    fs.mkdirSync(resolvedProfile, { recursive: true });

    const activePortFile = path.join(resolvedProfile, DEVTOOLS_ACTIVE_PORT);
    fs.rmSync(activePortFile, { force: true });

    const args = [
      `--user-data-dir=${resolvedProfile}`,
      '--remote-debugging-address=127.0.0.1',
      '--remote-debugging-port=0',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-background-networking',
      '--disable-component-update',
      'about:blank',
    ];
    if (this.headless) args.unshift('--headless=new');

    const child = spawn(this.executablePath, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });

    if (!child.pid) {
      child.kill();
      throw new Error('CHROMIUM_PID_MISSING');
    }

    let browser: Browser | null = null;
    try {
      const debugPort = await waitForDevToolsPort(resolvedProfile, child, this.launchTimeoutMs);
      const debugHost = '127.0.0.1' as const;
      const debugUrl = `http://${debugHost}:${debugPort}`;
      const response = await fetch(`${debugUrl}/json/version`, { signal: AbortSignal.timeout(this.launchTimeoutMs) });
      if (!response.ok) throw new Error(`CHROMIUM_DEBUG_ENDPOINT_HTTP_${response.status}`);
      browser = await chromium.connectOverCDP(debugUrl, { timeout: this.launchTimeoutMs });
      const handle: InternalHandle = {
        pid: child.pid,
        userDataDir: resolvedProfile,
        debugHost,
        debugPort,
        debugUrl,
        browser,
        process: child,
      };
      this.active = handle;
      return handle;
    } catch (error) {
      if (browser) await settleWithin(browser.close(), 1_000);
      terminateProcessTree(child.pid);
      await waitForExit(child, this.shutdownTimeoutMs).catch(() => false);
      fs.rmSync(activePortFile, { force: true });
      throw error;
    }
  }

  async stop(): Promise<void> {
    const handle = this.active;
    if (!handle) return;
    this.active = null;

    const activePortFile = path.join(handle.userDataDir, DEVTOOLS_ACTIVE_PORT);
    try {
      try {
        const session = await handle.browser.newBrowserCDPSession();
        await settleWithin(session.send('Browser.close'), 1_500);
      } catch {
        // Connection may already be closed; process cleanup below is authoritative.
      }
      await settleWithin(handle.browser.close(), 1_000);
      let exited = await waitForExit(handle.process, 2_000);
      if (!exited) {
        terminateProcessTree(handle.pid);
        exited = await waitForExit(handle.process, this.shutdownTimeoutMs);
      }
      if (!exited) throw new Error('CHROMIUM_SHUTDOWN_TIMEOUT');
    } finally {
      fs.rmSync(activePortFile, { force: true });
    }
  }

  async restart(userDataDir: string): Promise<BrowserRuntimeHandle> {
    const previous = this.active;
    if (previous && path.resolve(userDataDir) !== previous.userDataDir) {
      throw new Error('RESTART_PROFILE_MISMATCH');
    }
    await this.stop();
    return this.launch(userDataDir);
  }

  assertProfileWithin(profileRoot: string, userDataDir: string): void {
    if (!isPathInside(profileRoot, userDataDir)) throw new Error('BROWSER_PROFILE_OUTSIDE_ROOT');
  }
}
