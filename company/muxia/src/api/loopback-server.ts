import http, { type IncomingMessage, type ServerResponse } from 'node:http';

export const MX070_LEGACY_HOST = '127.0.0.1';
export const MX070_LEGACY_PORT = 3211;
const MAX_BODY_BYTES = 256 * 1024;

export interface LegacyChatCompletionRequest {
  model: string;
  messages?: unknown[];
  stream?: boolean;
  [key: string]: unknown;
}

export interface LegacyCompatExecutorResult {
  statusCode?: number;
  body: Record<string, unknown>;
}

export type LegacyCompatExecutor = (
  request: LegacyChatCompletionRequest,
) => Promise<LegacyCompatExecutorResult> | LegacyCompatExecutorResult;

export interface LegacyCompatServerOptions {
  executor: LegacyCompatExecutor;
  hostname?: string;
  port?: number;
}

function json(res: ServerResponse, statusCode: number, body: Record<string, unknown>): void {
  const payload = Buffer.from(JSON.stringify(body));
  res.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': String(payload.length),
    'cache-control': 'no-store',
  });
  res.end(payload);
}

async function readJson(req: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  let total = 0;
  for await (const chunk of req) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    total += buffer.length;
    if (total > MAX_BODY_BYTES) throw new Error('LEGACY_REQUEST_TOO_LARGE');
    chunks.push(buffer);
  }
  let value: unknown;
  try {
    value = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    throw new Error('LEGACY_REQUEST_JSON_INVALID');
  }
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('LEGACY_REQUEST_OBJECT_REQUIRED');
  return value as Record<string, unknown>;
}

export function createLegacyCompatibilityServer(options: LegacyCompatServerOptions) {
  const hostname = options.hostname ?? MX070_LEGACY_HOST;
  const port = options.port ?? MX070_LEGACY_PORT;
  if (hostname !== MX070_LEGACY_HOST) throw new Error('MX070_LOOPBACK_HOST_REQUIRED');
  if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('MX070_PORT_INVALID');

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', `http://${hostname}`);
      if (req.method === 'GET' && url.pathname === '/v1/models') {
        json(res, 200, {
          object: 'list',
          data: [{
            id: 'chatgpt',
            object: 'model',
            status: 'enabled',
            owned_by: 'muxia-compatibility',
            capabilities: ['image.generate'],
          }],
          compatibility: {
            version: 'mx070-legacy-proxima-v1',
            legacy_proxima_process: false,
            authority_expanded: false,
          },
        });
        return;
      }

      if (req.method === 'POST' && url.pathname === '/v1/chat/completions') {
        const body = await readJson(req);
        if (body.model !== 'chatgpt') throw new Error('LEGACY_MODEL_NOT_ALLOWED');
        if (body.stream === true) throw new Error('LEGACY_STREAMING_NOT_SUPPORTED');
        if (body.messages !== undefined && !Array.isArray(body.messages)) throw new Error('LEGACY_MESSAGES_INVALID');
        const result = await options.executor(body as LegacyChatCompletionRequest);
        const statusCode = result.statusCode ?? 200;
        if (!Number.isInteger(statusCode) || statusCode < 200 || statusCode > 599) throw new Error('LEGACY_EXECUTOR_STATUS_INVALID');
        json(res, statusCode, result.body);
        return;
      }

      json(res, 404, { error: { code: 'MX070_ROUTE_NOT_FOUND', message: 'route not found' } });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'MX070_UNKNOWN_ERROR';
      const clientError = message.startsWith('LEGACY_') || message.startsWith('MX070_');
      json(res, clientError ? 400 : 500, {
        error: { code: message, message: clientError ? 'legacy compatibility request rejected' : 'compatibility executor failed' },
      });
    }
  });

  return {
    hostname,
    port,
    server,
    async listen(): Promise<{ hostname: string; port: number }> {
      await new Promise<void>((resolve, reject) => {
        server.once('error', reject);
        server.listen(port, hostname, () => {
          server.off('error', reject);
          resolve();
        });
      });
      const address = server.address();
      if (!address || typeof address === 'string') throw new Error('MX070_SERVER_ADDRESS_UNAVAILABLE');
      return { hostname, port: address.port };
    },
    async close(): Promise<void> {
      if (!server.listening) return;
      await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
    },
  };
}
