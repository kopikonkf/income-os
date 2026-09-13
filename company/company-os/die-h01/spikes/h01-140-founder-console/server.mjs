import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {buildProviderBridgeReadModel, DEFAULT_RUNTIME} from './byok_bridge.mjs';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
export const HOST = process.env.H01_140_HOST || '127.0.0.1';
export const PORT = Number(process.env.H01_140_PORT || 20128);

const NOW = '2026-09-13T00:00:00Z';
const envelope = (source, data) => ({schema:'die.h01.founder-console.read.v1', read_only:true, source, observed_at:NOW, data});

const routes = new Map([
  ['/api/die/v1/overview', envelope('mission-control+h01', {mission_control:'GLOBAL_BRAIN', h01_runtime:'EXECUTION_PLANE', legacy_8876:'PRESERVED', console_mode:'SPIKE_READ_ONLY'})],
  ['/api/die/v1/production', envelope('h01-production-read-model', {lane:'VECTOR', mode:'VECTOR_OBJECT', form:'SINGLE', preset:'CLEAN_STOCK_VECTOR_V1', mutation:false})],
  ['/api/die/v1/providers', envelope('brave-fabric+provider-health+optional-api-bridge', {credential_values_exposed:false, live_connections_performed:false, profiles:'inventory-only', api_bridge:buildProviderBridgeReadModel(DEFAULT_RUNTIME)})],
  ['/api/die/v1/qc/gallery', envelope('h01-qc-read-model', {gallery:'read-only', generation_mutation:false, founder_qc_authority:'EXTERNAL'})],
  ['/api/die/v1/submission-ready', envelope('rights+qa+package-gates', {submission_action:'NONE', publication_action:'NONE', authority:'MISSION_CONTROL/FOUNDER'})],
  ['/api/die/v1/demand', envelope('demand-intelligence-read-model', {status:'read-only', can_reorder_live_queue:false})],
  ['/api/die/v1/tasks', envelope('mission-control-read-model', {scheduler:'MISSION_CONTROL', leases:'read-only', graph_authority:'MISSION_CONTROL'})],
  ['/api/die/v1/system/health', envelope('runtime-health-read-model', {console:'PASS', adapter:'PASS', upstream_9router_pin:'0.5.75', port_8876:'external-preserved'})],
  ['/api/die/v1/settings', envelope('console-visible-config', {secret_values_exposed:false, mutation:false, upstream_mode:'UI_SHELL_ONLY'})]
]);

const securityHeaders = {
  'content-security-policy': "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
  'x-content-type-options': 'nosniff',
  'x-frame-options': 'DENY',
  'referrer-policy': 'no-referrer',
  'cache-control': 'no-store'
};

function json(res, status, body, extra={}) {
  res.writeHead(status, {'content-type':'application/json; charset=utf-8', ...securityHeaders, ...extra});
  res.end(JSON.stringify(body));
}

export function createApp() {
  return http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname.startsWith('/api/die/v1/')) {
      if (req.method !== 'GET') return json(res, 405, {error:'READ_ONLY_CONTRACT', allowed:['GET']}, {'allow':'GET'});
      const payload = routes.get(url.pathname);
      if (!payload) return json(res, 404, {error:'NOT_FOUND'});
      return json(res, 200, payload);
    }
    if (url.pathname === '/healthz') return json(res, 200, {status:'PASS', mode:'READ_ONLY_SPIKE', live_provider_accounts:false, marketplace_actions:false});
    if (req.method !== 'GET' && req.method !== 'HEAD') return json(res, 405, {error:'READ_ONLY_CONSOLE'}, {'allow':'GET, HEAD'});
    if (url.pathname === '/' || url.pathname === '/index.html') {
      const html = await readFile(path.join(ROOT, 'public', 'index.html'));
      res.writeHead(200, {'content-type':'text/html; charset=utf-8', ...securityHeaders});
      if (req.method === 'HEAD') return res.end();
      return res.end(html);
    }
    return json(res, 404, {error:'NOT_FOUND'});
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const app = createApp();
  app.listen(PORT, HOST, () => console.log(JSON.stringify({status:'LISTENING', host:HOST, port:PORT, mode:'READ_ONLY_SPIKE'})));
}
